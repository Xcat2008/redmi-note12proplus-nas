#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 José Miranda (Xcat2008)
"""Stage first-boot prerequisites in an unpersonalized mounted build root only."""
from pathlib import Path
import argparse,json,shutil


def prepare(root,repo):
    root=Path(root).resolve();repo=Path(repo).resolve()
    if root==Path('/') or not (root/'etc/debian_version').is_file():raise ValueError('Separate mounted Debian build root required')
    if (root/'var/lib/redmi-nas/personalized').exists() or (root/'home/nas/.ssh/authorized_keys').exists():
        raise ValueError('Refusing a personalized system')
    for name in ['usr/bin/curl','usr/sbin/resize2fs']:
        if not (root/name).is_file():raise ValueError('Preinstall curl and e2fsprogs before image assembly: '+name)
    if list((root/'etc/ssh').glob('ssh_host_*_key')):raise ValueError('Remove build-time SSH host identities first')
    template=root/'etc/systemd/system/lxc@android.service'
    if 'ExecStartPre=/usr/bin/lxc-start -d -n android' not in template.read_text():raise ValueError('Unvalidated Android service template')
    def put(name,text,mode=0o644):
        path=root/name;path.parent.mkdir(parents=True,exist_ok=True)
        if not path.parent.resolve().is_relative_to(root):raise ValueError('Build path escapes root')
        path.write_text(text,encoding='utf-8');path.chmod(mode)
    put('etc/systemd/system/lxc@android.service.d/kvm-module-selection.conf',
        '[Unit]\nAfter=systemd-sysctl.service\n[Service]\nExecStartPre=\nExecStartPre=/usr/local/lib/redmi-nas/kvm-kernel/select-matching-modules.py\nExecStartPre=/usr/bin/lxc-start -d -n android\n')
    put('etc/sysctl.d/70-redmi-android-pids.conf','# Android 32-bit vendor services require thread IDs below 65536.\nkernel.pid_max = 65535\n')
    selector=root/'usr/local/lib/redmi-nas/kvm-kernel/select-matching-modules.py'
    selector.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(repo/'kernel/kvm/select_matching_modules.py',selector);selector.chmod(0o755)
    # Only remove this generic autostart link. Keep Android's dedicated unit.
    generic=root/'etc/systemd/system/multi-user.target.wants/lxc.service'
    if generic.is_symlink():generic.unlink()
    hosts=root/'etc/hosts';text=hosts.read_text()
    if not any('redmi-nas' in line.split('#',1)[0].split() for line in text.splitlines()):
        hosts.write_text(text.rstrip()+'\n127.0.1.1 redmi-nas\n')
    result={'bootstrapDependenciesPresent':True,'moduleSelectionBeforeAndroid':True,
            'steamNotRequiredForAndroidBoot':True,'personalized':False}
    put('usr/share/redmi-nas-hardware/bootstrap-preflight.json',json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True)
    args=parser.parse_args();print(json.dumps(prepare(args.root,Path(__file__).resolve().parents[1])))
