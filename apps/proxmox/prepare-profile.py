#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 José Miranda (Xcat2008)
"""Stage the clean optional profile. No phone boot-metadata writes or activation."""
from pathlib import Path
import argparse
import json
import os
import shutil
import subprocess


def put(root,name,text,mode=0o644):
    path=root/name.lstrip('/')
    if path.is_symlink():raise ValueError('Refusing to replace a symlink: '+name)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(text,encoding='utf-8',newline='\n');path.chmod(mode)


def configure(host,guest):
    """Write only a new, unpersonalized image, not an existing running NAS."""
    if not (guest/'usr/bin/pvesh').is_file():raise ValueError('Missing clean Proxmox package installation')
    if (guest/'var/lib/pve-cluster/config.db').exists():raise ValueError('Refusing an initialized account/VM database')
    if (host/'var/lib/redmi-nas/personalized').exists():raise ValueError('Refusing a personalized NAS')
    put(guest,'/etc/hostname','redmi-pve\n')
    put(guest,'/etc/hosts','127.0.0.1 localhost\n172.17.0.250 redmi-pve.local redmi-pve\n::1 localhost ip6-localhost\n')
    resolver=guest/'etc/resolv.conf'
    if resolver.is_symlink():resolver.unlink()
    put(guest,'/etc/resolv.conf','nameserver 1.1.1.1\nnameserver 9.9.9.9\n')
    put(guest,'/etc/network/interfaces','auto lo\niface lo inet loopback\n\nauto host0\niface host0 inet static\n    address 172.17.0.250/16\n    gateway 172.17.0.1\n\nauto vmbr0\niface vmbr0 inet static\n    address 10.77.0.1/24\n    bridge-ports none\n    bridge-stp off\n    bridge-fd 0\n')
    put(guest,'/usr/local/sbin/redmi-pve-network','''#!/bin/sh
set -eu
ip link set host0 up
ip address replace 172.17.0.250/16 dev host0
ip route replace default via 172.17.0.1 dev host0
ip link show vmbr0 >/dev/null 2>&1 || ip link add vmbr0 type bridge
ip address replace 10.77.0.1/24 dev vmbr0
ip link set vmbr0 up
sysctl -q -w net.ipv4.ip_forward=1
iptables -t nat -C POSTROUTING -s 10.77.0.0/24 -o host0 -j MASQUERADE 2>/dev/null || iptables -t nat -A POSTROUTING -s 10.77.0.0/24 -o host0 -j MASQUERADE
iptables -C FORWARD -i vmbr0 -o host0 -j ACCEPT 2>/dev/null || iptables -A FORWARD -i vmbr0 -o host0 -j ACCEPT
iptables -C FORWARD -i host0 -o vmbr0 -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT 2>/dev/null || iptables -A FORWARD -i host0 -o vmbr0 -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT
''',0o755)
    put(guest,'/etc/systemd/system/redmi-pve-network.service','''[Unit]
Description=Private Proxmox network
After=network-pre.target
Before=network.target
[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/local/sbin/redmi-pve-network
[Install]
WantedBy=multi-user.target
''')
    put(guest,'/etc/redmi-proxmox-dnsmasq.conf','''interface=vmbr0
bind-dynamic
except-interface=host0
dhcp-range=10.77.0.100,10.77.0.199,255.255.255.0,12h
dhcp-option=option:router,10.77.0.1
dhcp-option=option:dns-server,10.77.0.1
dhcp-leasefile=/var/lib/redmi-proxmox-dhcp/leases
no-resolv
server=1.1.1.1
server=9.9.9.9
domain=vm.redmi-nas
''')
    leases=guest/'var/lib/redmi-proxmox-dhcp';leases.mkdir(exist_ok=True);os.chown(leases,65534,65534);leases.chmod(0o750)
    put(guest,'/etc/systemd/system/redmi-proxmox-vm-network.service','''[Unit]
Description=Private guest DHCP and DNS
After=redmi-pve-network.service
Requires=redmi-pve-network.service
[Service]
ExecStart=/usr/sbin/dnsmasq --keep-in-foreground --conf-file=/etc/redmi-proxmox-dnsmasq.conf --user=nobody --group=nogroup
Restart=on-failure
RestartSec=5
[Install]
WantedBy=multi-user.target
''')
    put(guest,'/etc/systemd/system.conf.d/20-redmi-cpu.conf','[Manager]\nCPUAffinity=0 1 2 3 4 5 6 7\n')
    put(guest,'/usr/local/sbin/redmi-proxmox-scope-mounts','''#!/bin/sh
set -eu
for name in cpuinfo meminfo stat uptime swaps loadavg; do
 mount --bind "/run/redmi-lxcfs/proc/$name" "/proc/$name"
 mount -o remount,bind,ro "/proc/$name"
done
''',0o755)
    put(guest,'/etc/systemd/system/redmi-proxmox-scoped-metrics.service','''[Unit]
Description=Container-scoped resource metrics
After=local-fs.target
Before=pvestatd.service pvedaemon.service pveproxy.service
ConditionPathExists=/run/redmi-lxcfs/proc/meminfo
[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/local/sbin/redmi-proxmox-scope-mounts
[Install]
WantedBy=multi-user.target
''')
    for name in ['redmi-pve-network','redmi-proxmox-vm-network','redmi-proxmox-scoped-metrics']:
        subprocess.run(['systemctl','--root='+str(guest),'enable',name+'.service'],check=True,capture_output=True)
    for name in ['corosync','pve-ha-crm','pve-ha-lrm','watchdog-mux','pve-firewall','proxmox-firewall']:
        subprocess.run(['systemctl','--root='+str(guest),'disable',name+'.service'],check=False,capture_output=True)
    provider=host/'usr/local/lib/redmi-nas/proxmox-lxcfs';provider.mkdir(parents=True,exist_ok=True)
    for source,name in [('usr/bin/lxcfs','lxcfs'),('usr/lib/aarch64-linux-gnu/lxcfs/liblxcfs.so','liblxcfs.so')]:
        shutil.copyfile(guest/source,provider/name);(provider/name).chmod(0o755)
    (host/'var/lib/redmi-nas/proxmox-lxcfs').mkdir(parents=True,exist_ok=True)
    put(host,'/etc/systemd/system/redmi-proxmox-lxcfs.service','''[Unit]
Description=Scoped Proxmox metrics
After=local-fs.target
Before=redmi-proxmox-container.service
[Service]
Environment=LD_LIBRARY_PATH=/usr/local/lib/redmi-nas/proxmox-lxcfs
RuntimeDirectory=redmi-proxmox-lxcfs
ExecStart=/usr/local/lib/redmi-nas/proxmox-lxcfs/lxcfs -f -l --enable-cfs --runtime-dir=/run/redmi-proxmox-lxcfs -p /run/redmi-proxmox-lxcfs/lxcfs.pid /var/lib/redmi-nas/proxmox-lxcfs
ExecStopPost=-/usr/bin/fusermount3 -u /var/lib/redmi-nas/proxmox-lxcfs
Restart=on-failure
RestartSec=5
''')
    put(host,'/etc/systemd/system/redmi-proxmox-container.service','''[Unit]
Description=Optional isolated Proxmox environment
Requires=docker.service redmi-proxmox-lxcfs.service
After=docker.service redmi-proxmox-lxcfs.service
ConditionPathExists=/dev/kvm
ConditionPathExists=/var/lib/redmi-nas/proxmox-enabled
StartLimitIntervalSec=300
StartLimitBurst=3
[Service]
Type=notify
NotifyAccess=all
Delegate=yes
CPUAffinity=0 1 2 3 4 5 6 7
CPUQuota=800%
MemoryMax=3G
MemorySwapMax=1G
TasksMax=2048
Nice=5
KillMode=mixed
TimeoutStartSec=120
TimeoutStopSec=30
Restart=on-failure
RestartForceExitStatus=133
RestartSec=3
ExecStart=/usr/bin/systemd-nspawn --keep-unit --boot --register=yes --private-users=no --machine=redmi-pve --hostname=redmi-pve --directory=/userdata/redmi-nas/proxmox-rootfs --network-bridge=docker0 --bind=/dev/kvm --bind=/dev/fuse --bind=/dev/net/tun --capability=CAP_NET_ADMIN --bind-ro=/var/lib/redmi-nas/proxmox-lxcfs:/run/redmi-lxcfs
[Install]
WantedBy=multi-user.target
''')
    put(host,'/usr/local/lib/redmi-nas/proxmox-profile.json',json.dumps({'status':'preloaded-not-enabled','rootfs':'/userdata/redmi-nas/proxmox-rootfs','requires_actual_el2':True,'automatic_boot_metadata_writes':False,'account_created':False,'virtual_machines_included':False})+'\n')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--host-root',required=True,type=Path);parser.add_argument('--guest-root',required=True,type=Path)
    args=parser.parse_args()
    if args.host_root.resolve()==Path('/') or args.guest_root.resolve()==Path('/'):raise SystemExit('Only separate build roots are accepted')
    configure(args.host_root.resolve(),args.guest_root.resolve())
    print('Clean optional profile staged; no environment enabled or account created.')


if __name__=='__main__':main()
