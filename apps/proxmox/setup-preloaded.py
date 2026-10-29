#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 José Miranda (Xcat2008)
"""Enable an owned clean PVE root only after the real KVM/device preflight.

This never writes phone boot metadata, installs a kernel or starts a VM.
"""
from pathlib import Path
import argparse
import fcntl
import getpass
import hashlib
import json
import os
import platform
import stat
import subprocess
import tarfile

STATE=Path('/var/lib/redmi-nas/proxmox-distribution')
ROOT=Path('/userdata/redmi-nas/proxmox-rootfs')
BUNDLE=Path('/usr/share/redmi-nas-hardware/proxmox')


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(8*1024*1024),b''):h.update(block)
    return h.hexdigest()


def capability_errors(machine,release,parts,kvm_api):
    errors=[]
    if machine!='aarch64':errors.append('ARM64 required')
    if release!='4.19.191-g914ba8403bb3-dirty':errors.append('Unvalidated kernel')
    if parts!=[0xd05]*6+[0xd41]*2:errors.append('Unvalidated CPU layout')
    if kvm_api!=12:errors.append('Hardware KVM is not available; installing packages cannot activate EL2')
    return errors


def preflight():
    parts=[]
    for cpu in range(8):
        try:parts.append((int(Path(f'/sys/devices/system/cpu/cpu{cpu}/regs/identification/midr_el1').read_text(),16)>>4)&0xfff)
        except (OSError,ValueError):parts.append(-1)
    api=-1
    try:
        with open('/dev/kvm','rb',buffering=0) as device:
            api=fcntl.ioctl(device,0xae00,0)
            if api==12:
                vm=fcntl.ioctl(device,0xae01,0);os.close(vm)
    except OSError:api=-1
    return capability_errors(platform.machine(),platform.release(),parts,api)


def unpack():
    if not os.path.ismount('/userdata') or Path('/DATA').resolve()!=Path('/userdata/DATA'):
        raise ValueError('The native NAS data filesystem must be mounted first')
    receipt=STATE/'rootfs.json'
    if ROOT.exists():
        if receipt.is_file() and json.loads(receipt.read_text()).get('root')==str(ROOT):return
        raise ValueError('Existing Proxmox root is not owned by this installer')
    meta=json.loads((BUNDLE/'manifest.json').read_text());archive=BUNDLE/'rootfs.tar.gz'
    if sha(archive)!=meta['sha256']:raise ValueError('Clean Proxmox archive checksum mismatch')
    if os.statvfs('/userdata').f_bavail*os.statvfs('/userdata').f_frsize<meta['unpacked_bytes']+2*1024**3:raise ValueError('Insufficient data storage')
    temp=ROOT.with_name('proxmox-rootfs.preparing')
    if temp.exists():raise ValueError('Incomplete preparation exists; preserve it for diagnosis')
    temp.mkdir(parents=True)
    # Only the checksum-verified, locally shipped root archive is accepted.
    # Never extract into an existing installation or follow an external path.
    with tarfile.open(archive) as tar:
        for member in tar:
            path=Path(member.name)
            if path.is_absolute() or '..' in path.parts or member.isdev() or member.isfifo():raise ValueError('Unexpected clean-root archive member')
            if member.islnk() and (Path(member.linkname).is_absolute() or '..' in Path(member.linkname).parts):raise ValueError('Unsafe hard link')
    with tarfile.open(archive) as tar:
        tar.extractall(temp,filter='fully_trusted')
    temp.rename(ROOT)
    STATE.mkdir(parents=True,exist_ok=True);receipt.write_text(json.dumps({'root':str(ROOT),'archive_sha256':meta['sha256'],'accounts_from_author':False})+'\n')


def enable(password):
    errors=preflight()
    if errors:raise ValueError('; '.join(errors))
    if not isinstance(password,str) or not 8<=len(password)<=128 or any(ord(c)<32 for c in password):raise ValueError('Proxmox requires a password of 8–128 characters')
    cert=Path('/etc/nginx/redmi-retroarch/server.crt');key=cert.with_name('server.key')
    if not cert.is_file() or not key.is_file():raise ValueError('Complete NAS setup before enabling the Proxmox web entry')
    config=Path('/etc/nginx/sites-available/redmi-proxmox')
    link=Path('/etc/nginx/sites-enabled/redmi-proxmox')
    if config.exists() or config.is_symlink() or link.exists() or link.is_symlink():raise ValueError('Existing Proxmox proxy configuration is preserved')
    bridge=json.loads(subprocess.check_output(['docker','network','inspect','bridge'],text=True))[0]
    if bridge['IPAM']['Config'][0]['Subnet']!='172.17.0.0/16':raise ValueError('This candidate requires the default private Docker bridge; no existing network is changed')
    if any(v.get('IPv4Address','').split('/')[0]=='172.17.0.250' for v in bridge.get('Containers',{}).values()):raise ValueError('Private Proxmox address is already allocated')
    if subprocess.run(['ping','-c','1','-W','1','172.17.0.250'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0:raise ValueError('Private Proxmox address is already in use')
    unpack()
    if (ROOT/'var/lib/pve-cluster/config.db').exists():raise ValueError('Proxmox has already been initialized; existing accounts are preserved')
    subprocess.run(['chroot',str(ROOT),'chpasswd'],input=('root:'+password+'\n').encode(),check=True,stdout=subprocess.DEVNULL)
    STATE.mkdir(parents=True,exist_ok=True)
    marker=Path('/var/lib/redmi-nas/proxmox-enabled');marker.touch(mode=0o600)
    subprocess.run(['systemctl','daemon-reload'],check=True)
    subprocess.run(['systemctl','enable','--now','redmi-proxmox-container.service'],check=True)
    if subprocess.run(['systemctl','is-active','--quiet','redmi-proxmox-container']).returncode:raise ValueError('Proxmox did not start; no VM was created')
    config.write_text('''server {
 listen 8006 ssl;
 listen [::]:8006 ssl;
 server_name _;
 ssl_certificate /etc/nginx/redmi-retroarch/server.crt;
 ssl_certificate_key /etc/nginx/redmi-retroarch/server.key;
 client_max_body_size 0;
 location / {
  proxy_pass https://172.17.0.250:8006;
  proxy_http_version 1.1;
  proxy_set_header Host $http_host;
  proxy_set_header X-Forwarded-Proto $scheme;
  proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
  proxy_set_header Upgrade $http_upgrade;
  proxy_set_header Connection "upgrade";
  proxy_buffering off;
  proxy_request_buffering off;
  proxy_read_timeout 3600s;
 }
}
''')
    link.symlink_to(config)
    if subprocess.run(['nginx','-t'],capture_output=True).returncode:
        link.unlink();config.unlink();raise ValueError('Web proxy validation failed; previous sites preserved')
    subprocess.run(['systemctl','reload','nginx'],check=True)
    (STATE/'enabled.json').write_text(json.dumps({'enabled':True,'vm_created':False,'hardware_kvm':True,'web_port':8006})+'\n')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--enable',action='store_true');parser.add_argument('--unpack-only',action='store_true');args=parser.parse_args()
    if not args.enable and not args.unpack_only:
        errors=preflight();print(json.dumps({'ready':not errors,'errors':errors,'configuration_written':False}));return int(bool(errors))
    if os.geteuid()!=0:raise SystemExit('Run the installation step as root')
    if args.unpack_only:unpack();print('Clean Proxmox packages prepared; service remains disabled.');return 0
    password=getpass.getpass('Create the Proxmox root password (at least 8 characters): ')
    if password!=getpass.getpass('Repeat password: '):raise SystemExit('Passwords differ')
    enable(password);print('Proxmox enabled. Open HTTPS port 8006; account root, Linux PAM realm.');return 0


if __name__=='__main__':raise SystemExit(main())
