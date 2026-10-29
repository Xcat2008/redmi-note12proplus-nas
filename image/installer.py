#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Guarded installer client. --check never accesses or writes a phone."""
import argparse
import getpass
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import time
import urllib.request
import uuid
import zipfile

HERE=Path(sys.executable).resolve().parent if getattr(sys,'frozen',False) else Path(__file__).resolve().parent
SDK_URL='https://dl.google.com/android/repository/platform-tools-latest-windows.zip'

def checksum(path):
    digest=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(8*1024*1024),b''):digest.update(block)
    return digest.hexdigest()

def validate_sparse(path,expected_size):
    with path.open('rb') as f:
        data=f.read(28)
        if len(data)!=28:raise ValueError('Sparse image header missing')
        magic,major,minor,header,chunk_header,block,total,chunks,crc=struct.unpack('<IHHHHIIII',data)
        if (magic,major,header,chunk_header,block)!=(0xED26FF3A,1,28,12,4096):raise ValueError('Unsupported sparse image format')
        if total*block!=expected_size:raise ValueError('Unexpected filesystem capacity')
        accounted=0
        for _ in range(chunks):
            item=f.read(12)
            if len(item)!=12:raise ValueError('Truncated sparse chunk')
            kind,reserved,count,size=struct.unpack('<HHII',item)
            payload=size-12
            wanted={0xCAC1:count*block,0xCAC2:4,0xCAC3:0,0xCAC4:4}.get(kind)
            if wanted is None or payload!=wanted:raise ValueError('Invalid sparse chunk length')
            if kind!=0xCAC4:accounted+=count
            f.seek(payload,1)
            if f.tell()>path.stat().st_size:raise ValueError('Sparse chunk exceeds file')
        if accounted!=total or f.tell()!=path.stat().st_size:raise ValueError('Incomplete sparse image')

def inspect_package(folder):
    manifest=json.loads((folder/'installer-manifest.json').read_text(encoding='utf-8'))
    if manifest.get('model')!='22101316UG':raise ValueError('Wrong installer model')
    for name in ['boot.img','userdata.img']:
        spec=manifest['files'][name];file=folder/name
        print('Verifying',name,flush=True)
        if not file.is_file() or file.stat().st_size!=spec['bytes'] or checksum(file)!=spec['sha256']:raise ValueError('File size/checksum mismatch: '+name)
    validate_sparse(folder/'userdata.img',manifest['userdata_filesystem_bytes'])
    if (folder/'boot.img').stat().st_size!=134217728:raise ValueError('Unexpected boot partition image size')
    if manifest.get('requires_linux_vbmeta'):
        spec=manifest['files']['vbmeta.img'];file=folder/'vbmeta.img'
        if not file.is_file() or file.stat().st_size!=spec['bytes'] or checksum(file)!=spec['sha256']:raise ValueError('VBMeta size/checksum mismatch')
        validate_vbmeta(file)
    print('Image checks passed. No device accessed or changed.',flush=True)
    return manifest


def validate_vbmeta(path):
    data=path.read_bytes()
    if len(data)!=4096 or data[:4]!=b'AVB0' or struct.unpack_from('>I',data,120)[0]!=3:
        raise ValueError('Unexpected Linux VBMeta header or flags')

def locate_fastboot(folder,provided,authorize_download=None):
    if provided:
        path=Path(provided).resolve()
        if path.is_file():return str(path)
        raise ValueError('Selected fastboot executable does not exist')
    found=shutil.which('fastboot')
    if found:return found
    cached=folder/'tools/platform-tools/fastboot.exe'
    if cached.is_file():return str(cached)
    if os.name!='nt':raise ValueError('Install Android platform-tools first or use --fastboot PATH')
    print('Google Android Platform-Tools are required.')
    print('Download and license information: https://developer.android.com/tools/releases/platform-tools')
    approved=authorize_download() if authorize_download is not None else input('Download the official Windows tools now? Type YES: ').strip()=='YES'
    if not approved:raise ValueError('Platform-Tools download not authorized')
    cache=folder/'tools';cache.mkdir(exist_ok=True)
    archive=cache/'platform-tools.zip'
    urllib.request.urlretrieve(SDK_URL,archive)
    with zipfile.ZipFile(archive) as z:
        for member in z.infolist():
            if not (cache/member.filename).resolve().is_relative_to(cache.resolve()):raise ValueError('Unsafe tool archive path')
        z.extractall(cache)
    if not cached.is_file():raise ValueError('Official fastboot executable not found after extraction')
    return str(cached)

def command(executable,serial,*args,capture=True):
    result=subprocess.run([executable,'-s',serial,*args],capture_output=capture,text=True,errors='replace')
    text=(result.stdout or '')+(result.stderr or '')
    if result.returncode:raise ValueError('Fastboot command failed: '+' '.join(args)+'\n'+text)
    return text

def getvar(executable,serial,name):
    result=command(executable,serial,'getvar',name)
    match=re.search(r'(?:\(bootloader\)\s*)?'+re.escape(name)+r':\s*(\S+)',result)
    if not match:raise ValueError('Could not read required device property: '+name)
    return match.group(1)

def device_preflight(executable,manifest):
    found=subprocess.run([executable,'devices'],capture_output=True,text=True,check=True).stdout.splitlines()
    devices=[line.split()[0] for line in found if len(line.split())>=2 and line.split()[1]=='fastboot']
    if len(devices)!=1:raise ValueError('Exactly one phone must be connected in FASTBOOT mode')
    serial=devices[0]
    if getvar(executable,serial,'product')!='rubypro':raise ValueError('Connected phone is not the tested rubypro device')
    if getvar(executable,serial,'current-slot')!='a':raise ValueError('This candidate requires the documented factory firmware active in slot a')
    try:unlocked=getvar(executable,serial,'unlocked').lower() in ['yes','true','1']
    except ValueError:
        info=command(executable,serial,'oem','device-info')
        unlocked=bool(re.search(r'Device unlocked:\s*true',info,re.I))
    if not unlocked:raise ValueError('Bootloader must first be unlocked through Xiaomi')
    if int(getvar(executable,serial,'partition-size:boot_a'),16)!=134217728:raise ValueError('Unexpected boot_a partition size')
    if int(getvar(executable,serial,'partition-size:userdata'),16)!=manifest['userdata_partition_bytes']:raise ValueError('This candidate targets the documented256GB partition layout')
    if manifest.get('requires_linux_vbmeta') and int(getvar(executable,serial,'partition-size:vbmeta_a'),16)!=8388608:raise ValueError('Unexpected vbmeta_a partition size')
    return serial


def flash_images(executable,target,folder,manifest,capture=True):
    if manifest.get('requires_linux_vbmeta'):
        print('Writing Linux AVB metadata for the unlocked bootloader.',flush=True)
        command(executable,target,'flash','vbmeta_a',str(folder/'vbmeta.img'),capture=capture)
    print('Writing userdata. Do not disconnect the cable.',flush=True)
    command(executable,target,'-S','128M','flash','userdata',str(folder/'userdata.img'),capture=capture)
    print('Writing the boot image.',flush=True)
    command(executable,target,'flash','boot_a',str(folder/'boot.img'),capture=capture)

def make_setup_fields(pin,ssid='',password=''):
    if not re.fullmatch(r'[0-9]{4,12}',pin):raise ValueError('PIN must contain 4-12 digits')
    if ssid:
        if not 1<=len(ssid.encode())<=32 or any(ord(c)<32 for c in ssid):raise ValueError('Invalid Wi-Fi name')
        if not 8<=len(password)<=63 or any(ord(c)<32 for c in password):raise ValueError('Invalid WPA Wi-Fi password')
    directory=Path.home()/'.redmi-nas';directory.mkdir(mode=0o700,exist_ok=True)
    key=directory/('installer-'+uuid.uuid4().hex)
    subprocess.run(['ssh-keygen','-q','-t','ed25519','-N','','-C','redmi-nas-installer','-f',str(key)],check=True)
    public=key.with_suffix('.pub').read_text().strip()
    fields={'pin':pin,'ssh_public_key':public}
    if ssid:fields['wifi']={'ssid':ssid,'password':password}
    return fields,key


def personal_fields():
    while True:
        pin=getpass.getpass('Choose your own Linux/unlock PIN (4-12 digits): ')
        if re.fullmatch(r'[0-9]{4,12}',pin) and getpass.getpass('Repeat PIN: ')==pin:break
        print('PINs must match and contain4-12digits.')
    ssid=input('Wi-Fi name (leave empty to configure on the phone): ').strip()
    password=getpass.getpass('Wi-Fi password: ') if ssid else ''
    return make_setup_fields(pin,ssid,password)


def require_release(manifest,allow_untested=False):
    if allow_untested:return
    if not manifest.get('physical_install_test_passed'):
        raise ValueError('This candidate has not passed a clean physical installation test. Normal installation is disabled; use a tested release.')
    if not manifest.get('binary_redistribution_audit_passed'):
        raise ValueError('This package has not passed the binary redistribution review. Normal installation is disabled.')

def personalize(fields,timeout=240):
    import serial
    from serial.tools import list_ports
    until=time.monotonic()+timeout
    print('Waiting for one-time physical USB setup...',flush=True)
    while time.monotonic()<until:
        ports=[p.device for p in list_ports.comports() if p.vid==0x1D6B and p.pid==0x0104]
        for port in ports:
            try:
                with serial.Serial(port,115200,timeout=2,write_timeout=5) as link:
                    ready_until=time.monotonic()+12
                    while time.monotonic()<ready_until:
                        if b'REDMI-NAS-SETUP/1 READY' in link.readline():break
                    else:continue
                    link.write(json.dumps(fields).encode()+b'\n');link.flush()
                    reply_until=time.monotonic()+120
                    while time.monotonic()<reply_until:
                        line=link.readline().decode(errors='replace').strip()
                        if not line.startswith('{'):continue
                        result=json.loads(line)
                        if result.get('status')=='ok':return result
                        if result.get('status')=='error':raise ValueError('Phone setup rejected the fields; settings were not logged')
            except (serial.SerialException,OSError):pass
        time.sleep(2)
    raise ValueError('USB setup did not complete. Keep the cable connected and rerun with --personalize-only.')

def main():
    parser=argparse.ArgumentParser(description='Redmi NAS candidate installer; checks are the default')
    parser.add_argument('--folder',type=Path,default=HERE)
    parser.add_argument('--install',action='store_true')
    parser.add_argument('--personalize-only',action='store_true')
    parser.add_argument('--allow-untested',action='store_true')
    parser.add_argument('--fastboot')
    args=parser.parse_args()
    folder=args.folder.resolve()
    if args.personalize_only:
        fields,key=personal_fields();personalize(fields);print('Setup completed. Keep your private SSH key at:',key);return
    manifest=inspect_package(folder)
    if not args.install:return
    require_release(manifest,args.allow_untested)
    import serial  # fail before any device write if the dependency is absent
    executable=locate_fastboot(folder,args.fastboot)
    target=device_preflight(executable,manifest)
    print('This will ERASE Android and every file/account on the connected phone.')
    print('Required model:22101316UG. Required factory firmware:',manifest['factory_firmware'])
    if input('Confirm the model printed on your phone: ').strip()!='22101316UG':raise ValueError('Model not confirmed')
    if input('Confirm matching factory firmware version: ').strip()!=manifest['factory_firmware']:raise ValueError('Factory firmware not confirmed')
    if input('Type ERASE THIS PHONE to install: ').strip()!='ERASE THIS PHONE':raise ValueError('No erase authorized')
    fields,key=personal_fields()
    flash_images(executable,target,folder,manifest,capture=False)
    command(executable,target,'reboot',capture=False)
    personalize(fields)
    print('Linux image installed and personalized. The NAS installs after internet is available.')
    print('Your private SSH key stays on this computer:',key)
    print('Open http://redmi-nas.local after NAS setup and create your own Homeio account.')

if __name__=='__main__':
    try:main()
    except (ValueError,OSError,subprocess.SubprocessError) as error:print('STOP:',error,file=sys.stderr);sys.exit(1)
