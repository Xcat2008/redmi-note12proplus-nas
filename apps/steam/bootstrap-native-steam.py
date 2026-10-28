#!/usr/bin/python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Fetch verified official programs into a fresh NAS-owned native client home."""
from pathlib import Path,PurePosixPath
import concurrent.futures,hashlib,json,os,shutil,stat,struct,urllib.request,zipfile

BASE=Path('/DATA/AppData/custom-steam')
CLIENT=BASE/'native-arm64/home/.local/share/Steam'
ORIGIN='https://client-update.fastly.steamstatic.com/'
PACKAGE_MANIFEST=Path('/usr/local/share/redmi-nas/steam/native-packages.json')
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as stream:
  for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
 return h.hexdigest()
def extract(archive,destination):
 root=destination.resolve()
 with zipfile.ZipFile(archive) as package:
  for entry in package.infolist():
   relative=PurePosixPath(entry.filename.replace('\\','/'))
   if relative.is_absolute() or '..' in relative.parts:raise RuntimeError('Unsafe official archive path')
   if not relative.parts:continue
   target=destination.joinpath(*relative.parts)
   if not target.resolve().is_relative_to(root):raise RuntimeError('Archive escaped staging directory')
   mode=(entry.external_attr>>16)&0xffff
   if entry.is_dir():target.mkdir(parents=True,exist_ok=True);continue
   target.parent.mkdir(parents=True,exist_ok=True)
   if stat.S_ISLNK(mode):
    link=package.read(entry).decode().replace('\\','/')
    if not (target.parent/link).resolve().is_relative_to(root):raise RuntimeError('Unsafe official archive symlink')
    target.unlink(missing_ok=True);target.symlink_to(link)
   else:
    if target.is_symlink():target.unlink()
    with package.open(entry) as source,target.open('wb') as out:shutil.copyfileobj(source,out)
    with target.open('rb') as stream:header=stream.read(4)
    target.chmod(0o755 if header==b'\x7fELF' or header.startswith(b'#!') or target.suffix=='.sh' else (mode&0o777 or 0o644))
def main():
 if os.geteuid()!=32011:raise RuntimeError('Run official client staging as the NAS account')
 if CLIENT.exists():
  with (CLIENT/'steamrtarm64/steam').open('rb') as stream:header=stream.read(20)
  if header[:4]!=b'\x7fELF' or struct.unpack('<H',header[18:20])[0]!=183:raise RuntimeError('Existing client is not the native ARM64 profile')
  print(json.dumps({'nativeClientAlreadyPresent':True,'existingAccountUntouched':True}));return
 packages=json.loads(PACKAGE_MANIFEST.read_text())
 cache=BASE/'recovery/packages';cache.mkdir(mode=0o700,parents=True,exist_ok=True)
 def download(p):
  if '/' in p['file'] or '\\' in p['file'] or '..' in p['file']:raise RuntimeError('Invalid pinned package name')
  target=cache/p['file']
  if not target.exists() or target.stat().st_size!=p['size'] or sha(target)!=p['sha256']:
   temporary=target.with_suffix('.partial')
   with urllib.request.urlopen(ORIGIN+p['file'],timeout=120) as source,temporary.open('wb') as out:shutil.copyfileobj(source,out)
   if temporary.stat().st_size!=p['size'] or sha(temporary)!=p['sha256']:raise RuntimeError('Official client checksum mismatch')
   temporary.replace(target);target.chmod(0o600)
  return target
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
  archives=list(pool.map(download,packages))
 stage=BASE/'native-arm64/program-staging'
 if stage.exists():raise RuntimeError('Incomplete earlier staging exists; inspect before retrying')
 stage.mkdir(mode=0o700,parents=True)
 for archive in archives:extract(archive,stage)
 with (stage/'steamrtarm64/steam').open('rb') as stream:header=stream.read(20)
 if header[:4]!=b'\x7fELF' or struct.unpack('<H',header[18:20])[0]!=183:raise RuntimeError('Official program architecture mismatch')
 CLIENT.parent.mkdir(mode=0o700,parents=True,exist_ok=True);stage.rename(CLIENT)
 home=BASE/'native-arm64/home';links=home/'.steam';links.mkdir(mode=0o700,exist_ok=True)
 for name,target in [('root',CLIENT),('steam',CLIENT),('sdk64',CLIENT/'linuxarm64')]:
  p=links/name
  if not p.exists():p.symlink_to(target)
 (BASE/'recovery/packages.json').write_text(json.dumps(packages))
 (BASE/'recovery/known-good.json').write_text(json.dumps({'version':'1792618285','purpose':'Official program recovery only','automaticNasBackupsEnabled':False}))
 print(json.dumps({'officialNativePackagesVerified':len(packages),'newAccountRequired':True,'userDataCopied':False}))
if __name__=='__main__':main()
