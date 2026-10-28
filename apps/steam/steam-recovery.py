#!/usr/bin/python3
"""Verify or restore only the cached, validated Steam program payload."""
from pathlib import Path,PurePosixPath
import hashlib,json,os,shutil,stat,sys,zipfile
BASE=Path('/DATA/AppData/custom-steam')
RECOVERY=BASE/'recovery'
CLIENT=BASE/'native-arm64/home/.local/share/Steam'
PROTECTED={'config','userdata','steamapps','logs','appcache','depotcache','package','controller_base','skins'}

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()

def restore(target,write):
    packages=json.loads((RECOVERY/'packages.json').read_text())
    for p in packages:
        archive=RECOVERY/'packages'/p['file']
        if archive.stat().st_size!=p['size'] or digest(archive)!=p['sha256']:
            raise RuntimeError('Recovery archive checksum failed')
    count=0;protected=0
    root=target.resolve()
    for package in packages:
        with zipfile.ZipFile(RECOVERY/'packages'/package['file']) as archive:
            for entry in archive.infolist():
                rel=PurePosixPath(entry.filename.replace('\\','/'))
                if rel.is_absolute() or '..' in rel.parts:raise RuntimeError('Unsafe program path')
                if not rel.parts:continue
                if rel.parts[0] in PROTECTED or rel.parts[0].startswith(('ssfn','.')):
                    protected+=1;continue
                path=target.joinpath(*rel.parts)
                if not path.parent.resolve().is_relative_to(root):raise RuntimeError('Program path escaped client')
                mode=(entry.external_attr>>16)&0xffff
                if entry.is_dir():
                    if write:path.mkdir(parents=True,exist_ok=True)
                    continue
                if stat.S_ISLNK(mode):
                    link=archive.read(entry).decode().replace('\\','/')
                    if not (path.parent/link).resolve().is_relative_to(root):raise RuntimeError('Unsafe program symlink')
                    if write:
                        path.parent.mkdir(parents=True,exist_ok=True)
                        tmp=path.with_name(path.name+'.recovery-new')
                        if tmp.exists() or tmp.is_symlink():tmp.unlink()
                        tmp.symlink_to(link);tmp.replace(path)
                else:
                    count+=1
                    if write:
                        path.parent.mkdir(parents=True,exist_ok=True)
                        tmp=path.with_name(path.name+'.recovery-new')
                        if tmp.is_symlink():raise RuntimeError('Unsafe recovery temporary path')
                        with archive.open(entry) as source,tmp.open('wb') as out:shutil.copyfileobj(source,out)
                        with tmp.open('rb') as f:header=f.read(4)
                        executable=header==b'\x7fELF' or header.startswith(b'#!') or path.suffix=='.sh'
                        tmp.chmod(0o755 if executable else 0o644);tmp.replace(path)
    return {'verifiedArchives':len(packages),'programFiles':count,'protectedEntriesSkipped':protected,'written':write}

if __name__=='__main__':
    command=sys.argv[1] if len(sys.argv)==2 else ''
    if command not in ['verify','restore','rehearse']:raise SystemExit('Choose verify, restore or rehearse')
    if command in ['restore','rehearse'] and os.geteuid()==0:raise SystemExit('Run program extraction as the NAS user')
    if command=='rehearse':
        target=RECOVERY/'restore-rehearsal'
        if target.exists():raise SystemExit('A recovery rehearsal already exists; inspect it first')
        target.mkdir(mode=0o700)
        result=restore(target,True)
        # Validate only fixed program identities, never account/library contents.
        import struct
        result['arm64ProgramsVerified']=all(struct.unpack('<H',(target/name).read_bytes()[18:20])[0]==183 for name in ['steamrtarm64/steam','steamrtarm64/steamwebhelper'])
        if not result['arm64ProgramsVerified']:raise SystemExit('Recovery architecture verification failed')
        shutil.rmtree(target)
    else:result=restore(CLIENT,command=='restore')
    print(json.dumps(result))
