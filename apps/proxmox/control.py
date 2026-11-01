#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 José Miranda (Xcat2008)
"""Local, authenticated-web-UI backend for optional Proxmox setup.

This helper never flashes firmware, reboots the NAS, or issues a guest-start command.
Existing Proxmox guest-autostart rules are managed by Proxmox itself.
The web server must authenticate and check the request origin before invoking it.
"""
from pathlib import Path
import fcntl
import json
import os
import runpy
import stat
import subprocess
import sys
import tempfile
import time
import ssl
import urllib.request

RUNTIME=Path('/run/redmi-proxmox-setup')
STATE=Path('/var/lib/redmi-nas/proxmox-distribution')
MARKER=Path('/var/lib/redmi-nas/proxmox-enabled')
SETUP=Path('/usr/local/sbin/redmi-proxmox-setup')
UNIT='redmi-proxmox-container.service'


def runtime_status():
    result=subprocess.run(['systemctl','show',UNIT,'--property=ActiveState,SubState,UnitFileState'],capture_output=True,text=True,timeout=4)
    if result.returncode:raise ValueError('Could not read the optional Proxmox service.')
    fields=dict(line.split('=',1) for line in result.stdout.splitlines() if '=' in line)
    running=fields.get('ActiveState')=='active'
    web_ready=False
    if running:
        # This is a loopback health probe of our own self-signed NAS proxy.
        # Browser certificate handling and the user's login are unchanged.
        try:
            with urllib.request.urlopen('https://127.0.0.1:8006/',timeout=1,context=ssl._create_unverified_context()) as response:
                web_ready=response.status==200
        except (OSError,ValueError):pass
    return {'running':running,'starting':fields.get('ActiveState')=='activating',
            'webReady':web_ready,'autostartEnabled':fields.get('UnitFileState') in ('enabled','enabled-runtime')}


def runtime_directory():
    RUNTIME.mkdir(mode=0o700,exist_ok=True)
    info=RUNTIME.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid!=0 or stat.S_IMODE(info.st_mode)!=0o700:
        raise ValueError('Unexpected setup runtime directory')


def write_job(value):
    runtime_directory()
    with tempfile.NamedTemporaryFile(mode='w',dir=RUNTIME,delete=False,encoding='utf-8') as stream:
        json.dump(value,stream);temporary=Path(stream.name)
    os.replace(temporary,RUNTIME/'job.json')


def job_status():
    path=RUNTIME/'job.json'
    if not path.exists():return {'state':'idle'}
    if path.is_symlink():raise ValueError('Unexpected setup status path')
    value=json.loads(path.read_text())
    if value.get('state') in ['queued','running']:
        result=subprocess.run(['systemctl','is-active','--quiet','redmi-proxmox-setup.service'],capture_output=True,timeout=3)
        if result.returncode and time.time()-value.get('updatedAt',0)>20:
            return {'state':'failed','error':'Setup stopped before completion. Inspect the setup service log before retrying.'}
    return value


def status():
    job=job_status()
    configured=MARKER.is_file() and (STATE/'enabled.json').is_file()
    errors=[]
    if not configured and job['state'] not in ['queued','running']:
        if not SETUP.is_file():errors=['The clean optional Proxmox package is not included in this installation.']
        else:errors=runpy.run_path(str(SETUP))['preflight']()
    return {'configured':configured,'ready':not errors,'errors':errors,
            'busy':job['state'] in ['queued','running'],'job':job,'webPort':8006,
            'loginUser':'root','loginRealm':'Linux PAM','defaultEnabled':False,
            **(runtime_status() if configured else {'running':False,'starting':False,'webReady':False,'autostartEnabled':False})}


def start_existing():
    current=status()
    if not current['configured']:raise ValueError('Set up Proxmox before starting it.')
    if current['busy']:raise ValueError('Proxmox setup is in progress.')
    # Only the pre-existing owned service can be started. Existing accounts,
    # guest settings and any guest autostart policy are preserved.
    if not current['running'] and not current['starting']:
        subprocess.run(['systemctl','start','--no-block',UNIT],capture_output=True,check=True,timeout=6)
    return status()


def set_autostart(enabled):
    if type(enabled) is not bool:raise ValueError('Choose whether Proxmox starts with the NAS.')
    current=status()
    if not current['configured']:raise ValueError('Set up Proxmox first.')
    if current['busy']:raise ValueError('Proxmox setup is in progress.')
    subprocess.run(['systemctl','enable' if enabled else 'disable',UNIT],capture_output=True,check=True,timeout=6)
    return status()


def validate_password(password):
    if not isinstance(password,str) or not 8<=len(password)<=128 or any(ord(c)<32 for c in password):
        raise ValueError('Choose a password with 8–128 characters.')


def queue_setup(password):
    validate_password(password);runtime_directory()
    lock=os.open(RUNTIME/'setup.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    try:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        current=status()
        if current['configured']:raise ValueError('Proxmox is already configured. Existing accounts are preserved.')
        if current['busy']:raise ValueError('Proxmox setup is already in progress.')
        if not current['ready']:raise ValueError('; '.join(current['errors']))
        with tempfile.NamedTemporaryFile(mode='w',dir=RUNTIME,prefix='secret-',delete=False,encoding='utf-8') as stream:
            stream.write(password);secret=Path(stream.name)
        write_job({'state':'queued','updatedAt':time.time()})
        try:
            subprocess.run(['systemd-run','--unit=redmi-proxmox-setup','--collect',
                '--property=UMask=0077','--property=TimeoutStartSec=20min',
                '--','/usr/bin/python3',str(Path(__file__).resolve()),'worker',str(secret)],
                check=True,capture_output=True,timeout=8)
        except Exception:
            secret.unlink(missing_ok=True)
            write_job({'state':'failed','updatedAt':time.time(),'error':'Could not start the setup service.'})
            raise ValueError('Could not start the setup service.') from None
    finally:os.close(lock)
    return status()


def worker(secret):
    runtime_directory();secret=Path(secret)
    if secret.parent!=RUNTIME or not secret.name.startswith('secret-'):
        raise ValueError('Invalid setup secret path')
    fd=os.open(secret,os.O_RDONLY|os.O_NOFOLLOW)
    try:
        info=os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid!=0 or stat.S_IMODE(info.st_mode)!=0o600 or info.st_size>512:
            raise ValueError('Invalid setup secret permissions')
        with os.fdopen(fd,encoding='utf-8') as stream:password=stream.read(513)
        fd=-1;validate_password(password)
        secret.unlink()
        write_job({'state':'running','updatedAt':time.time()})
        runpy.run_path(str(SETUP))['enable'](password)
        write_job({'state':'succeeded','updatedAt':time.time()})
    except Exception as error:
        message=str(error) if isinstance(error,ValueError) else 'Setup failed. Inspect redmi-proxmox-setup.service for details.'
        write_job({'state':'failed','updatedAt':time.time(),'error':message})
        raise SystemExit(1)
    finally:
        if fd>=0:os.close(fd)
        secret.unlink(missing_ok=True)


def main():
    if os.geteuid()!=0:raise ValueError('Native NAS service privileges are required')
    action=sys.argv[1] if len(sys.argv)>1 else 'status'
    if action=='worker' and len(sys.argv)==3:worker(sys.argv[2]);return
    if action=='status':data=status()
    elif action=='start' and len(sys.argv)==2:data=start_existing()
    elif action=='set-autostart' and len(sys.argv)==2:
        raw=sys.stdin.buffer.read(2049)
        if len(raw)>2048:raise ValueError('Request is too large')
        value=json.loads(raw)
        if not isinstance(value,dict) or set(value)!={'enabled'}:raise ValueError('Choose an autostart setting')
        data=set_autostart(value['enabled'])
    elif action=='enable':
        raw=sys.stdin.buffer.read(2049)
        if len(raw)>2048:raise ValueError('Request is too large')
        value=json.loads(raw)
        if not isinstance(value,dict) or set(value)!={'password'}:raise ValueError('Choose a setup password')
        data=queue_setup(value['password'])
    else:raise ValueError('Unknown setup action')
    print(json.dumps({'data':data}))


if __name__=='__main__':
    try:main()
    except (ValueError,OSError,subprocess.SubprocessError) as error:
        print(json.dumps({'error':str(error) if isinstance(error,ValueError) else 'Optional setup is unavailable.'}));raise SystemExit(1)
