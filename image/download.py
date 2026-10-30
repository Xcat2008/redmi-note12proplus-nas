#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Download the fixed release parts, verify them and open the Windows assistant.

The release build embeds download-manifest.json alongside this module. This
program never connects to a phone and never installs drivers or changes policy.
"""
import hashlib
import json
from pathlib import Path, PurePosixPath
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
import urllib.request
import zipfile

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(8*1024**2),b''):h.update(chunk)
    return h.hexdigest()

def safe_name(name):
    if not name or Path(name).name!=name or any(c in name for c in '/\\:') or name in ('.','..'):
        raise ValueError('Unsafe release filename')
    return name

def validate_manifest(data):
    if data.get('repository')!='Xcat2008/redmi-note12proplus-nas' or data.get('tag')!='v0.2.0-rc3':
        raise ValueError('Unexpected release')
    for item in data['parts']+[data['archive']]:
        safe_name(item['name'])
        if item['bytes']<=0 or len(item['sha256'])!=64 or any(c not in '0123456789abcdef' for c in item['sha256']):
            raise ValueError('Invalid release digest')
    safe_name(data['folder'])
    if sum(x['bytes'] for x in data['parts'])!=data['archive']['bytes']:
        raise ValueError('Inconsistent release sizes')
    return data

def fetch_part(item,folder,url,notify):
    target=folder/safe_name(item['name'])
    if target.exists():
        if target.stat().st_size==item['bytes'] and digest(target)==item['sha256']:return target
        raise ValueError('An existing file has a different checksum: '+target.name)
    partial=target.with_name(target.name+'.download')
    offset=partial.stat().st_size if partial.exists() else 0
    if offset>item['bytes']:raise ValueError('Oversized incomplete download: '+partial.name)
    if offset<item['bytes']:
        request=urllib.request.Request(url,headers={'Range':f'bytes={offset}-'} if offset else {})
        with urllib.request.urlopen(request,timeout=60) as response:
            if offset and response.status!=206:offset=0
            if offset and response.headers.get('Content-Range','').split('/')[0]!=f"bytes {offset}-{item['bytes']-1}":
                raise ValueError('Unexpected download range')
            with partial.open('ab' if offset else 'wb') as output:
                while chunk:=response.read(1024**2):
                    offset+=len(chunk)
                    if offset>item['bytes']:raise ValueError('Download exceeds the release size')
                    output.write(chunk);notify(f'{target.name}: {offset/1024**2:.0f} / {item["bytes"]/1024**2:.0f} MiB')
    if partial.stat().st_size!=item['bytes'] or digest(partial)!=item['sha256']:
        raise ValueError('Download checksum failed: '+partial.name+'. Keep it for diagnosis; remove only this incomplete file before retrying.')
    partial.rename(target)
    return target

def extract_checked(archive,folder,expected_root):
    with zipfile.ZipFile(archive) as bundle:
        for item in bundle.infolist():
            name=PurePosixPath(item.filename)
            if name.is_absolute() or '..' in name.parts or not name.parts or name.parts[0]!=expected_root or '\\' in item.filename or ':' in item.filename:
                raise ValueError('Unsafe package path')
            if (item.external_attr>>16)&0o170000==0o120000:raise ValueError('Unexpected package symlink')
        if bundle.testzip() is not None:raise ValueError('Package CRC check failed')
        bundle.extractall(folder)

def install_download(data,folder,notify):
    validate_manifest(data);folder.mkdir(parents=True,exist_ok=True)
    destination=folder/data['folder']
    if destination.exists():
        raise ValueError('The installation folder already exists. Choose another download folder; existing files were preserved.')
    required=data['archive']['bytes']*2+data['unpackedBytes']+1024**3
    if shutil.disk_usage(folder).free<required:raise ValueError(f'Allow at least {required/1024**3:.1f} GiB free in this download folder.')
    base='https://github.com/'+data['repository']+'/releases/download/'+data['tag']+'/'
    parts=[fetch_part(item,folder,base+item['name'],notify) for item in data['parts']]
    zipped=folder/data['archive']['name']
    if zipped.exists():
        if zipped.stat().st_size!=data['archive']['bytes'] or digest(zipped)!=data['archive']['sha256']:
            raise ValueError('An existing ZIP has a different checksum')
    else:
        partial=zipped.with_name(zipped.name+'.joining')
        if partial.exists():raise ValueError('An incomplete ZIP exists. Preserve or remove that .joining file before retrying.')
        notify('Joining verified parts…')
        with partial.open('xb') as output:
            for part in parts:
                with part.open('rb') as stream:shutil.copyfileobj(stream,output,8*1024**2)
        if digest(partial)!=data['archive']['sha256']:raise ValueError('Joined ZIP checksum failed')
        partial.rename(zipped)
    notify('Verifying and extracting the package…')
    with tempfile.TemporaryDirectory(prefix='.redmi-nas-extract-',dir=folder) as temporary:
        staging=Path(temporary)
        assert staging.resolve().is_relative_to(folder.resolve())
        extract_checked(zipped,staging,data['folder'])
        if digest(staging/data['folder']/'RedmiNAS-Setup.exe')!=data['setupSha256']:
            raise ValueError('Assistant checksum failed')
        if destination.exists():raise ValueError('Installation folder appeared during download; existing files preserved')
        (staging/data['folder']).rename(destination)
    setup=destination/'RedmiNAS-Setup.exe'
    notify('Download verified. Opening the assistant; the phone is still unchanged.')
    subprocess.Popen([str(setup)],cwd=destination)

def main():
    import tkinter as tk
    from tkinter import filedialog,messagebox,ttk
    resources=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent))
    data=validate_manifest(json.loads((resources/'download-manifest.json').read_text(encoding='utf-8')))
    selftest=len(sys.argv)==3 and sys.argv[1]=='--self-test-output'
    root=tk.Tk();root.title('Redmi NAS — Download 0.2.0-rc3');root.geometry('650x300')
    if selftest:root.withdraw()
    status=tk.StringVar(value='Experimental release · Redmi Note 12 Pro+ 5G 22101316UG / 256 GB only')
    ttk.Label(root,text='Redmi NAS · José Miranda (Xcat2008)',font=('',16)).pack(pady=18)
    ttk.Label(root,text='Download, verify and open the installation assistant.\nInstallation requires Xiaomi bootloader unlock and erases the phone.',justify='center').pack(pady=8)
    ttk.Label(root,textvariable=status,wraplength=600,justify='center').pack(pady=15)
    events=queue.Queue();busy=False
    def start():
        nonlocal busy
        target=filedialog.askdirectory(title='Choose a download folder with sufficient free space')
        if not target:return
        busy=True;button.configure(state='disabled')
        def work():
            try:install_download(data,Path(target),lambda text:events.put(('status',text)));events.put(('done',None))
            except Exception as error:events.put(('error',str(error)))
        threading.Thread(target=work,daemon=True).start()
    button=ttk.Button(root,text='Download and verify',command=start);button.pack(pady=8)
    def poll():
        nonlocal busy
        while not events.empty():
            kind,value=events.get_nowait()
            if kind=='status':status.set(value)
            else:
                busy=False;button.configure(state='normal')
                if kind=='error':status.set('Download stopped; existing files preserved.');messagebox.showerror('Redmi NAS',value)
        root.after(150,poll)
    def close():
        if not busy or messagebox.askyesno('Redmi NAS','Stop this download? Verified parts can be reused next time.'):root.destroy()
    root.protocol('WM_DELETE_WINDOW',close)
    if selftest:
        root.update_idletasks()
        Path(sys.argv[2]).write_text(json.dumps({'guiConstructed':True,'manifestValidated':True,'networkAccessed':False,'phoneAccessed':False,'partCount':len(data['parts'])})+'\n')
        root.destroy();return
    root.after(150,poll);root.mainloop()

if __name__=='__main__':main()
