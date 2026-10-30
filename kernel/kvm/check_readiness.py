#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 José Miranda (Xcat2008)
"""Inspect KVM readiness without writing boot metadata or starting a guest."""
import argparse
import errno
import json
import os
import platform
from pathlib import Path

KERNELS={'4.19.191-g914ba8403bb3','4.19.191-g914ba8403bb3-dirty'}

def classify(machine,release,api,error=None):
    known=machine=='aarch64' and release in KERNELS
    if not known:
        return {'stage':'unsupported-profile','ready':False,'next':'Use the exact tested phone, firmware and NAS kernel profile.'}
    if api==12:
        return {'stage':'kvm-api-available','ready':True,'next':'Homeio Settings → Performance → Virtual machines · Proxmox can run its final capability checks and optional setup.'}
    if error in (errno.EACCES,errno.EPERM):
        return {'stage':'permissions-required','ready':False,'next':'Run this diagnostic with sudo. A permission failure does not prove missing EL2.'}
    return {'stage':'platform-or-kernel-not-ready','ready':False,'next':'Check the boot EL2 handoff and matching KVM-enabled kernel. Xiaomi bootloader unlock alone does not enable KVM. Do not treat installing Proxmox packages as platform activation.'}

def inspect_kvm(device=Path('/dev/kvm')):
    import fcntl
    api=None;error=None
    try:
        descriptor=os.open(device,os.O_RDONLY|os.O_CLOEXEC)
        try:api=fcntl.ioctl(descriptor,0xae00,0)
        finally:os.close(descriptor)
    except OSError as failure:error=failure.errno
    machine=platform.machine();release=platform.release()
    return dict(classify(machine,release,api,error),architecture=machine,kernel=release,kvmApiVersion=api,errorNumber=error,
                bootMetadataWritten=False,firmwareWritten=False,guestStarted=False,privateIdentifiersRead=False,
                scope='KVM API availability only. Optional Proxmox setup also tests VM creation. This diagnostic does not activate EL2.')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    print(json.dumps(inspect_kvm(),ensure_ascii=False,indent=2))

if __name__=='__main__':main()
