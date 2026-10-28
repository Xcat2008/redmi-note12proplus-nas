#!/usr/bin/python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Finish a new NAS profile without importing author accounts or media."""
from pathlib import Path
import json,os,subprocess,ipaddress

REPO=Path(__file__).resolve().parents[1]
def owned_directory(path,mode=0o755):
 p=Path(path);p.mkdir(parents=True,exist_ok=True);p.chmod(mode);os.chown(p,32011,32011);return p
def new_file(path,data,mode=0o644,owner=True):
 p=Path(path)
 if not p.exists():
  p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data);p.chmod(mode)
  if owner:os.chown(p,32011,32011)
 return p
def main():
 if os.geteuid()!=0:raise RuntimeError('Administrator access required')
 steam=owned_directory('/DATA/AppData/custom-steam',0o700)
 for folder in ['bin','logs','runtime','native-arm64','native-arm64/home','recovery']:
  owned_directory(steam/folder,0o700)
 p=steam/'bin/start-steam';p.write_bytes((REPO/'apps/steam/start-steam-gpu').read_bytes());p.chmod(0o755)
 for folder in ['ROMs','ROMs/MegaDrive','ROMs/PS1','ROMs/PS2','BIOS','BIOS/PS2','Saves','States','Screenshots']:
  owned_directory('/DATA/Games/'+folder)
 for folder in ['native','native/playlists','armsx2-system','armsx2-system/pcsx2','armsx2-system/pcsx2/bios']:
  owned_directory('/DATA/AppData/custom-retroarch/'+folder)
 bios=Path('/DATA/AppData/custom-retroarch/armsx2-system/pcsx2/bios')
 if not bios.is_symlink():
  try:bios.rmdir()
  except OSError:pass
  else:bios.symlink_to('/DATA/Games/BIOS/PS2',target_is_directory=True)
 new_file('/DATA/AppData/custom-retroarch/native/retroarch.cfg',(REPO/'apps/retroarch/retroarch-homeio.cfg').read_bytes())
 cores=owned_directory('/home/nas/.local/share/retroarch/cores')
 info=owned_directory('/home/nas/.local/share/retroarch/info')
 info.joinpath('armsx2_gles_libretro.info').write_text('display_name = "Sony - PlayStation 2 (ARMSX2 - Mali)"\ncorename = "ARMSX2 - Mali"\nmanufacturer = "Sony"\nsupported_extensions = "iso|bin|chd|cso|gz|elf"\n')
 info.joinpath('genesis_plus_gx_libretro.info').write_text('display_name = "Sega - Mega Drive / Genesis (Genesis Plus GX)"\ncorename = "Genesis Plus GX"\nmanufacturer = "Sega"\nsupported_extensions = "md|gen|smd|bin|sms|gg|sg|cue|chd"\n')
 for p in info.glob('*.info'):os.chown(p,32011,32011)
 import shutil
 profiles=REPO/'apps/retroarch/controller-profiles'
 destination=owned_directory('/home/nas/.local/share/retroarch/autoconfig')
 shutil.copytree(profiles,destination,dirs_exist_ok=True)
 for parent,dirs,files in os.walk(destination):
  os.chown(parent,32011,32011)
  for name in files:os.chown(Path(parent)/name,32011,32011)
 # Use upstream generic defaults. Do not copy the owner's per-game speed hacks.
 config=owned_directory('/DATA/AppData/custom-retroarch/config/.config/sunshine',0o700)
 client=Path('/usr/local/share/redmi-nas/gaming/gaming-launch-client.py')
 destination=Path('/DATA/AppData/custom-retroarch/config/gaming-launch-client.py')
 destination.write_bytes(client.read_bytes());destination.chmod(0o755);os.chown(destination,32011,32011)
 resource=Path('/usr/local/share/redmi-nas/retroarch/armsx2-resources')
 if resource.is_dir():
  import shutil
  destination=Path('/DATA/AppData/custom-retroarch/armsx2-system/pcsx2/resources')
  shutil.copytree(resource,destination,dirs_exist_ok=True)
  for parent,dirs,files in os.walk(destination):
   os.chown(parent,32011,32011)
   for name in files:os.chown(Path(parent)/name,32011,32011)
 apps=config/'apps.json';data=json.loads(apps.read_text()) if apps.exists() else {'env':{},'apps':[]}
 defaults={'Desktop','Low Res Desktop','Steam Big Picture','Steam','RetroArch'}
 preserved=[a for a in data.get('apps',[]) if a.get('name') not in defaults]
 data['apps']=[{'name':'RetroArch','detached':['/usr/bin/python3 /config/gaming-launch-client.py retroarch'],'image-path':'desktop.png'},
               {'name':'Steam','detached':['/usr/bin/python3 /config/gaming-launch-client.py steam'],'image-path':'steam.png'}]+preserved
 apps.write_text(json.dumps(data,indent=2)+'\n');apps.chmod(0o600);os.chown(apps,32011,32011)
 p=config/'sunshine.conf';s=p.read_text() if p.exists() else 'sunshine_name = Redmi NAS\ncapture = x11\nencoder = software\nsw_preset = ultrafast\nsystem_tray = disabled\nupnp = disabled\n'
 hosts=['localhost','127.0.0.1','redmi-nas.local']
 for value in subprocess.check_output(['hostname','-I'],text=True).split():
  try:
   if ipaddress.ip_address(value).version==4:hosts.append(value)
  except ValueError:pass
 values={'file_apps':'/config/.config/sunshine/apps.json','csrf_allowed_origins':','.join('https://'+h+':3444' for h in dict.fromkeys(hosts))}
 lines=[line for line in s.splitlines() if line.split('=',1)[0].strip() not in values]
 p.write_text('\n'.join(lines)+'\n'+'\n'.join(k+' = '+v for k,v in values.items())+'\n');p.chmod(0o600);os.chown(p,32011,32011)
 # Preserve any choice on an existing installation. A clean image has no markers.
 for name,value in [('memory-extension.json',{'enabled':False,'sizeBytes':4294967296}),('battery-charge.json',{'enabled':False,'mode':'xiaomi-native-75-80'})]:
  new_file('/var/lib/redmi-nas/'+name,(json.dumps(value)+'\n').encode(),0o600,owner=False)
 nginx=Path('/etc/nginx/sites-available/redmi-retroarch');nginx.write_bytes((REPO/'apps/steam/redmi-gaming.conf').read_bytes())
 p=Path('/etc/nginx/sites-available/redmi-sunshine')
 s=p.read_text().replace('proxy_set_header Host $host;','proxy_set_header Host $http_host;')
 if 'proxy_set_header X-Forwarded-Proto' not in s:s=s.replace('proxy_set_header Cookie "";','proxy_set_header Cookie "";\n  proxy_set_header X-Forwarded-Proto $scheme;')
 p.write_text(s)
 print(json.dumps({'newProfileConfigured':True,'separateShortcuts':True,'defaultMemoryExtension':False,'defaultBatteryCare':False,'privateStateImported':False}))
if __name__=='__main__':main()
