#!/usr/bin/python3
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 José Miranda (Xcat2008)
"""Non-installing checks for maintenance of an existing isolated KVM profile."""
import fcntl
import json
import os
from pathlib import Path
import platform
import subprocess
import sys


def inventory_errors(architecture, kernel, container, major, parts, api, version):
    errors = []
    if architecture != 'aarch64':
        errors.append('This profile requires ARM64')
    if kernel != '4.19.191-g914ba8403bb3-dirty':
        errors.append('The running kernel is outside the validated KVM profile')
    if container != 'systemd-nspawn':
        errors.append('Run inside the existing isolated Proxmox environment, not the NAS host')
    if major != '13':
        errors.append('The validated Proxmox userspace is Debian 13')
    if parts != [0xd05] * 6 + [0xd41] * 2:
        errors.append('Physical CPU layout does not match the tested Dimensity 1080')
    if api != 12:
        errors.append('Usable KVM API is unavailable; installing userspace cannot enable EL2')
    if version != '9.2.20':
        errors.append('The installed pve-manager version has not been validated by this source profile')
    return errors


def read(path):
    try:
        return Path(path).read_text().strip()
    except OSError:
        return ''


def main():
    parts = []
    for cpu in range(8):
        value = read(f'/sys/devices/system/cpu/cpu{cpu}/regs/identification/midr_el1')
        parts.append((int(value, 16) >> 4) & 0xfff if value else -1)
    api = -1
    try:
        with open('/dev/kvm', 'rb', buffering=0) as device:
            api = fcntl.ioctl(device, 0xae00, 0)
            # Validate VM allocation, then immediately release it. No vCPU or
            # guest instruction is created; no configuration is written.
            vm = fcntl.ioctl(device, 0xae01, 0)
            os.close(vm)
    except OSError:
        api = -1
    package = subprocess.run(['dpkg-query', '-W', '-f=${Version}', 'pve-manager'],
                             capture_output=True, text=True)
    errors = inventory_errors(platform.machine(), platform.release(),
                              read('/run/systemd/container'),
                              read('/etc/debian_version').split('.')[0], parts,
                              api, package.stdout.strip())
    required = ['/usr/share/perl5/PVE/ProcFSTools.pm',
                '/usr/share/perl5/PVE/QemuServer/Drive.pm', '/usr/bin/kvm']
    if not all(Path(path).exists() for path in required):
        errors.append('An existing Proxmox installation is required')
    print(json.dumps({'ready': not errors, 'profile': 'existing-isolated-proxmox',
                      'errors': errors, 'configuration_written': False}))
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
