#!/usr/bin/python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 José Miranda (Xcat2008)
"""Guarded compatibility for the tested EDK2 SEC early identity-map entry.

The default command audits the diverted vendor firmware without writing files.
--apply is used by the isolated Proxmox maintenance installer and APT hook.
No phone firmware, GPT, boot partition or EFI variable store is modified.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import struct

SUPPORTED_SHA256 = {'3f9b9b65fa6e5b31b67e7b6a8f8142b6df7c1afe0255ef9cc3b6431678ea8611'}
VENDOR = Path('/usr/share/pve-edk2-firmware/AAVMF_CODE.fd.redmi-vendor')
TARGET = Path('/usr/share/pve-edk2-firmware/AAVMF_CODE.fd')


def patch_early_map(data):
    """Replace exactly one known entry branch, preserving all other bytes."""
    matches = []
    start = 0
    while True:
        offset = data.find(bytes.fromhex('404238d5'), start)
        if offset < 0:
            break
        start = offset + 4
        if offset % 4 or offset + 20 > len(data):
            continue
        words = struct.unpack_from('<5I', data, offset)
        if (words[1] & 0xfff8001f != 0x36180000
                or words[2] != 0xd5380720 or words[3] != 0xf2780c1f
                or words[4] & 0xff00001f != 0x54000000):
            continue
        immediate = (words[4] >> 5) & 0x7ffff
        if immediate & (1 << 18):
            immediate -= 1 << 19
        destination = offset + 16 + immediate * 4
        if (0 < destination - offset < 512 and destination + 4 <= len(data)
                and struct.unpack_from('<I', data, destination)[0] & 0xfc000000 == 0x14000000):
            matches.append((offset, destination))
    if len(matches) != 1:
        raise ValueError('Unrecognized EDK2 SEC layout; no compatibility file was written')
    offset, destination = matches[0]
    result = bytearray(data)
    struct.pack_into('<I', result, offset, 0x14000000 | (((destination - offset) // 4) & 0x3ffffff))
    return bytes(result), {'offset': offset, 'destination': destination, 'changed_instructions': 1}


def transform_vendor(data, kernel):
    source_hash = hashlib.sha256(data).hexdigest()
    active = kernel.startswith('4.19.')
    if active and source_hash not in SUPPORTED_SHA256:
        raise ValueError('Vendor firmware digest is not validated for this profile; review the update first')
    result, detail = patch_early_map(data) if active else (data, {'changed_instructions': 0})
    return result, dict(detail, workaround_active=active, vendor_sha256=source_hash,
                        runtime_sha256=hashlib.sha256(result).hexdigest(), kernel=kernel,
                        phone_boot_firmware_changed=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='write the container runtime copy')
    args = parser.parse_args()
    result, receipt = transform_vendor(VENDOR.read_bytes(), platform.release())
    if args.apply:
        temporary = TARGET.with_name(TARGET.name + '.redmi-new')
        temporary.write_bytes(result)
        temporary.chmod(0o644)
        os.replace(temporary, TARGET)
        state = Path('/var/lib/redmi-proxmox')
        state.mkdir(parents=True, exist_ok=True)
        (state / 'firmware-compatibility.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(dict(receipt, configuration_written=args.apply)))


if __name__ == '__main__':
    main()
