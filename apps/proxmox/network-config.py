#!/usr/bin/python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Register the existing private bridge after PVE's first initialization."""
from pathlib import Path
import json

INTERFACES='''auto lo
iface lo inet loopback

auto host0
iface host0 inet static
    address 172.17.0.250/16
    gateway 172.17.0.1

auto vmbr0
iface vmbr0 inet static
    address 10.77.0.1/24
    bridge-ports none
    bridge-stp off
    bridge-fd 0
'''

def register(root=Path('/')):
    root=Path(root)
    if not (root/'usr/bin/pvesh').is_file():raise ValueError('Only the isolated Proxmox root is accepted')
    path=root/'etc/network/interfaces'
    if path.is_symlink():raise ValueError('Preserve an unexpected network symlink')
    old=path.read_text()
    lines=[line.strip() for line in old.splitlines() if line.strip() and not line.lstrip().startswith('#')]
    if lines!=['auto lo','iface lo inet loopback','iface eth0 inet manual']:
        return {'changed':False,'existingConfigurationPreserved':True}
    backup=path.with_name('interfaces.before-redmi-registration')
    if not backup.exists():backup.write_text(old)
    path.write_text(INTERFACES)
    return {'changed':True,'bridge':'vmbr0','networkReloaded':False}

if __name__=='__main__':print(json.dumps(register()))
