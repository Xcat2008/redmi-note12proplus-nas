#!/usr/bin/python3
"""Expose Xiaomi's native 75–80% charge window, without changing safety limits."""
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time

NODE = Path('/sys/class/power_supply/battery/night_charging')
CONFIG = Path('/var/lib/redmi-nas/battery-charge.json')
UNIT = 'redmi-battery-care.service'

def read(path):
    try: return Path(path).read_text().strip()
    except OSError: return None

def configured():
    try: return json.loads(CONFIG.read_text()).get('enabled') is True
    except (OSError, ValueError): return False

def state():
    raw=read(NODE);capacity=read('/sys/class/power_supply/battery/capacity')
    temp=read('/sys/class/power_supply/battery/temp')
    return dict(supported=raw in ('0','1'), enabled=configured(), active=raw=='1',
                lowerPercent=75, upperPercent=80,
                capacityPercent=int(capacity) if capacity and capacity.isdigit() else None,
                temperatureC=int(temp)/10 if temp and temp.lstrip('-').isdigit() else None,
                chargingStatus=read('/sys/class/power_supply/battery/status'),
                powerPathEnabled=read('/proc/mtk_battery_cmd/en_power_path')=='1')

def write_config(enabled):
    tmp=CONFIG.with_suffix('.new')
    tmp.write_text(json.dumps(dict(enabled=enabled,mode='xiaomi-native-75-80'))+'\n')
    tmp.chmod(0o600);tmp.replace(CONFIG)

def set_mode(enabled):
    if not state()['supported']:
        raise RuntimeError('The native Xiaomi charging control is unavailable.')
    NODE.write_text('1\n' if enabled else '0\n')
    if read(NODE) != ('1' if enabled else '0'):
        raise RuntimeError('The controller did not accept the charging mode.')

def main():
    action=sys.argv[1] if len(sys.argv)==2 else ''
    if action not in ('status','enable','disable','boot'):
        raise RuntimeError('Unknown battery operation.')
    if action=='status':return state()
    if os.geteuid()!=0:raise RuntimeError('Administrator access is required.')
    with open('/run/lock/redmi-battery-care.lock','w') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise RuntimeError('A battery operation is already in progress.')
        if action=='boot':
            if not configured():return state()
            for _ in range(90):
                if NODE.exists():break
                time.sleep(1)
            set_mode(True)
        else:
            enabled=action=='enable';previous=state()['active']
            set_mode(enabled)
            result=subprocess.run(['systemctl','enable' if enabled else 'disable',UNIT],capture_output=True,timeout=20)
            if result.returncode:
                set_mode(previous)
                raise RuntimeError('The startup preference could not be saved.')
            write_config(enabled)
        return state()

if __name__=='__main__':
    try:print(json.dumps(dict(data=main())))
    except Exception as error:
        print(json.dumps(dict(error=str(error) if isinstance(error,RuntimeError) else 'The battery setting could not be changed.')))
        sys.exit(1)
