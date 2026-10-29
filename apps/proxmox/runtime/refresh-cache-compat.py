#!/usr/bin/python3
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 José Miranda (Xcat2008)
"""Reapply only the diverted QEMU launcher after package maintenance."""
from pathlib import Path
import os,ctypes,hashlib,json
base=Path('/usr/local/lib/redmi-proxmox');vendor=Path('/usr/bin/kvm.redmi-vendor')
assert vendor.is_file() and os.access(vendor,os.X_OK),'Missing diverted vendor QEMU'
library=base/'libredmi-kvm-cache-affinity.so';ctypes.CDLL(str(library))
source=base/'kvm-launcher.sh';target=Path('/usr/bin/kvm');temp=Path('/usr/bin/kvm.redmi-new')
text=source.read_bytes();assert b'exec -a /usr/bin/kvm /usr/bin/kvm.redmi-vendor' in text
temp.write_bytes(text);temp.chmod(0o755);os.replace(temp,target)
state=Path('/var/lib/redmi-proxmox');state.mkdir(exist_ok=True)
(state/'cache-compatibility.json').write_text(json.dumps({'scope':'QEMU cache-description ioctls only','guestExecutionRestricted':False,'metadataCpuCluster':'Cortex-A78 CPUs6/7','librarySha256':hashlib.sha256(library.read_bytes()).hexdigest(),'sourceSha256':hashlib.sha256((base/'redmi-kvm-cache-affinity.c').read_bytes()).hexdigest(),'kernelChanged':False},indent=2))
print('Redmi Proxmox QEMU cache compatibility: verified')
