#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""One-time onboarding over physically connected USB; never a root shell."""
import base64
import json
import os
from pathlib import Path
import pwd
import re
import select
import struct
import subprocess
import time
import tty

STATE=Path('/var/lib/redmi-nas/personalized')

def validate(data):
    if not isinstance(data,dict):raise ValueError('Expected setup object')
    pin=data.get('pin','')
    if not isinstance(pin,str) or not re.fullmatch(r'[0-9]{4,12}',pin):raise ValueError('Invalid PIN')
    key=data.get('ssh_public_key','')
    if not isinstance(key,str) or '\n' in key or '\r' in key:raise ValueError('Invalid public key')
    fields=key.split()
    if len(fields)<2 or fields[0]!='ssh-ed25519':raise ValueError('Ed25519 key required')
    try:
        raw=base64.b64decode(fields[1],validate=True)
        size=struct.unpack('>I',raw[:4])[0]
        length=struct.unpack('>I',raw[4+size:8+size])[0]
        if raw[4:4+size]!=b'ssh-ed25519' or length!=32 or len(raw)!=8+size+32:raise ValueError()
    except (ValueError,struct.error):raise ValueError('Malformed public key') from None
    wifi=data.get('wifi')
    if wifi is not None:
        if not isinstance(wifi,dict):raise ValueError('Invalid Wi-Fi object')
        ssid,password=wifi.get('ssid',''),wifi.get('password','')
        if not isinstance(ssid,str) or not 1<=len(ssid.encode())<=32 or any(ord(c)<32 for c in ssid):raise ValueError('Invalid SSID')
        if not isinstance(password,str) or not 8<=len(password)<=63 or any(ord(c)<32 for c in password):raise ValueError('Invalid WPA password')
    return {'pin':pin,'ssh_public_key':' '.join(fields[:2]),'wifi':wifi}

def apply(data):
    data=validate(data)
    subprocess.run(['chpasswd'],input=('nas:'+data['pin']+'\n').encode(),check=True,stdout=subprocess.DEVNULL)
    folder=Path('/home/nas/.ssh');folder.mkdir(mode=0o700,parents=True,exist_ok=True)
    key=folder/'authorized_keys';key.write_text(data['ssh_public_key']+'\n');os.chmod(key,0o600)
    user=pwd.getpwnam('nas')
    for p in (folder,key):os.chown(p,user.pw_uid,user.pw_gid)
    subprocess.run(['ssh-keygen','-A'],check=True,stdout=subprocess.DEVNULL)
    if data['wifi']:
        network=data['wifi']
        subprocess.run(['nmcli','connection','add','type','wifi','ifname','wlan0','con-name','NAS-WiFi','ssid',network['ssid']],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        subprocess.run(['nmcli','connection','modify','NAS-WiFi','wifi-sec.key-mgmt','wpa-psk','wifi-sec.psk',network['password'],'connection.autoconnect','yes'],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:subprocess.run(['nmcli','connection','up','NAS-WiFi'],check=False,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=45)
        except subprocess.TimeoutExpired:pass  # Wi-Fi can also be configured locally after setup.
    STATE.parent.mkdir(parents=True,exist_ok=True);STATE.write_text('Personalized over physical USB.\n');os.chmod(STATE,0o600);os.sync()

def main():
    if STATE.exists():return
    until=time.monotonic()+180
    while not Path('/dev/ttyGS0').exists():
        if time.monotonic()>until:raise RuntimeError('USB setup interface unavailable')
        time.sleep(1)
    fd=os.open('/dev/ttyGS0',os.O_RDWR|os.O_NOCTTY)
    try:
        tty.setraw(fd);buffer=b'';last=0
        while not STATE.exists():
            if time.monotonic()-last>2:os.write(fd,b'REDMI-NAS-SETUP/1 READY\n');last=time.monotonic()
            if not select.select([fd],[],[],1)[0]:continue
            buffer+=os.read(fd,4096)
            if len(buffer)>8192:buffer=b'';continue
            if b'\n' not in buffer:continue
            line,buffer=buffer.split(b'\n',1)
            try:apply(json.loads(line))
            except ValueError:os.write(fd,b'{"status":"error","reason":"invalid setup fields"}\n');continue
            except (OSError,subprocess.SubprocessError):os.write(fd,b'{"status":"error","reason":"setup incomplete"}\n');continue
            os.write(fd,b'{"status":"ok","hostname":"redmi-nas","personalized":true}\n')
    finally:os.close(fd)

if __name__=='__main__':main()
