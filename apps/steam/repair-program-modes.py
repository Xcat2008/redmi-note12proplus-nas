#!/usr/bin/python3
"""Restore executable modes omitted by some ARM64 client archives."""
from pathlib import Path
import os,stat,struct

def repair(root):
    fixed=0
    for folder in ['steamrtarm64','linuxarm64']:
        for p in (root/folder).rglob('*'):
            if p.is_symlink() or not p.is_file() or p.stat().st_mode&stat.S_IXUSR:continue
            if not p.resolve().is_relative_to(root.resolve()):continue
            with p.open('rb') as f:header=f.read(4)
            if header==b'\x7fELF' or header.startswith(b'#!'):
                p.chmod(p.stat().st_mode|stat.S_IXUSR|stat.S_IXGRP|stat.S_IXOTH);fixed+=1
    return fixed

if __name__=='__main__':
    root=Path('/DATA/AppData/custom-steam/native-arm64/home/.local/share/Steam')
    repair(root)
    with (root/'steamrtarm64/steam').open('rb') as f:header=f.read(20)
    if header[:4]!=b'\x7fELF' or struct.unpack('<H',header[18:20])[0]!=183:
        raise SystemExit('The installed Steam program is not ARM64. Use the validated recovery command.')
