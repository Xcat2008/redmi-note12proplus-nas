#!/usr/bin/python3
"""Optional disk swap for the NAS. Existing vendor ZRAM is never reconfigured."""
import fcntl
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import time

BASE = Path('/userdata/redmi-nas-swap')
SWAP = BASE / 'reserve.swap'
CONFIG = Path('/var/lib/redmi-nas/memory-extension.json')
SIZE = 4 * 1024**3
UNIT = 'redmi-memory-extension.service'

def swaps():
    result = []
    for line in Path('/proc/swaps').read_text().splitlines()[1:]:
        p, kind, size, used, priority = line.split()
        result.append(dict(path=p, sizeBytes=int(size)*1024, usedBytes=int(used)*1024, priority=int(priority)))
    return result

def memory_available():
    for line in Path('/proc/meminfo').read_text().splitlines():
        if line.startswith('MemAvailable:'):
            return int(line.split()[1])*1024
    return 0

def can_disable(available, used):
    return available >= used + 512*1024**2

def state():
    entries = swaps()
    disk = next((x for x in entries if x['path'] == str(SWAP)), None)
    zram = [x for x in entries if 'zram' in x['path']]
    try:
        enabled = json.loads(CONFIG.read_text()).get('enabled') is True
    except (OSError, ValueError):
        enabled = False
    fs = os.statvfs('/userdata')
    return dict(enabled=enabled, active=disk is not None, sizeBytes=SIZE,
                usedBytes=disk['usedBytes'] if disk else 0,
                reservedBytes=SWAP.stat().st_size if SWAP.is_file() else 0,
                availableStorageBytes=fs.f_bavail*fs.f_frsize,
                zramTotalBytes=sum(x['sizeBytes'] for x in zram),
                zramUsedBytes=sum(x['usedBytes'] for x in zram),
                availableMemoryBytes=memory_available(),
                kvmAvailable=Path('/dev/kvm').exists())

def command(*args, timeout=30):
    r = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    if r.returncode:
        raise RuntimeError('The memory service could not complete '+args[0]+'.')

def save(enabled):
    tmp = CONFIG.with_suffix('.new')
    tmp.write_text(json.dumps(dict(enabled=enabled, sizeBytes=SIZE))+'\n')
    tmp.chmod(0o600)
    tmp.replace(CONFIG)

def trusted_directory():
    BASE.mkdir(mode=0o700, exist_ok=True)
    st = BASE.lstat()
    if not stat.S_ISDIR(st.st_mode) or st.st_uid != 0 or st.st_mode & 0o077:
        raise RuntimeError('The private swap directory has unsafe permissions.')
    if SWAP.exists() or SWAP.is_symlink():
        st = SWAP.lstat()
        if not stat.S_ISREG(st.st_mode) or st.st_uid != 0 or st.st_nlink != 1 or st.st_mode & 0o077:
            raise RuntimeError('The private swap file has unsafe permissions.')

def enable(boot=False):
    if boot and not state()['enabled']:
        return
    trusted_directory()
    zram = [x for x in swaps() if 'zram' in x['path']]
    if boot:
        for _ in range(90):
            if zram:
                break
            time.sleep(1)
            zram = [x for x in swaps() if 'zram' in x['path']]
    if not zram:
        raise RuntimeError('ZRAM must be active before enabling storage extension.')
    if not state()['active']:
        if not SWAP.exists():
            if state()['availableStorageBytes'] < SIZE + 2*1024**3:
                raise RuntimeError('Keep at least 2 GiB of storage free after creating the reserve.')
            fd = os.open(SWAP, os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW, 0o600)
            os.close(fd)
            try:
                command('dd', 'if=/dev/zero', 'of='+str(SWAP), 'bs=1M', 'count=4096', 'conv=fsync', 'status=none', timeout=180)
                command('mkswap', str(SWAP))
                command('swapon', str(SWAP))
            except Exception:
                if not state()['active']:
                    SWAP.unlink(missing_ok=True)
                raise
        else:
            if SWAP.stat().st_size != SIZE:
                raise RuntimeError('The reserved file has an unexpected size.')
            command('swapon', str(SWAP))
        current = next(x for x in swaps() if x['path'] == str(SWAP))
        if current['priority'] >= min(x['priority'] for x in zram):
            command('swapoff', str(SWAP), timeout=120)
            raise RuntimeError('Storage extension must have lower priority than ZRAM.')
    if not boot:
        save(True)
        command('systemctl', 'enable', UNIT)

def disable():
    trusted_directory()
    current = next((x for x in swaps() if x['path'] == str(SWAP)), None)
    if current:
        if not can_disable(memory_available(), current['usedBytes']):
            raise RuntimeError('Close memory-heavy applications before disabling the extension.')
        command('swapoff', str(SWAP), timeout=120)
    save(False)
    command('systemctl', 'disable', UNIT)
    SWAP.unlink(missing_ok=True)

def main():
    action = sys.argv[1] if len(sys.argv) == 2 else ''
    if action not in ('status','enable','disable','boot'):
        raise RuntimeError('Unknown memory operation.')
    if action == 'status':
        return state()
    if os.geteuid() != 0:
        raise RuntimeError('Administrator access is required.')
    with open('/run/lock/redmi-memory-extension.lock', 'w') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError('A memory operation is already in progress.')
        if action in ('enable','boot'):
            enable(action == 'boot')
        else:
            disable()
        return state()

if __name__ == '__main__':
    try:
        print(json.dumps(dict(data=main())))
    except Exception as error:
        message = str(error) if isinstance(error, RuntimeError) else 'The memory operation failed; the previous state was preserved where possible.'
        print(json.dumps(dict(error=message)))
        sys.exit(1)
