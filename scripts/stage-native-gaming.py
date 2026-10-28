#!/usr/bin/python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Install the source-controlled native profile; DESTDIR stages a clean image."""
from pathlib import Path
import os,sys,shutil,json,hashlib

REPO=Path(__file__).resolve().parents[1]
PREFIX=Path(os.environ.get('DESTDIR','/')).absolute()
BUNDLE=Path(os.environ.get('REDMI_NAS_GAMING_BUNDLE','/usr/share/redmi-nas-hardware/gaming'))
def target(path):
 p=Path(path);assert p.is_absolute() and '..' not in p.parts
 return PREFIX/p.relative_to('/')
def put(path,data,mode=0o644):
 p=target(path);p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data);p.chmod(mode)
def text(path,data,mode=0o644):put(path,data.encode(),mode)
def source(relative,path,mode=0o644):put(path,(REPO/relative).read_bytes().replace(b'\r\n',b'\n'),mode)
def unit(name,data,enabled=False):
 text('/etc/systemd/system/'+name,data)
 if enabled:
  p=target('/etc/systemd/system/multi-user.target.wants/'+name);p.parent.mkdir(parents=True,exist_ok=True)
  if not p.exists() and not p.is_symlink():p.symlink_to('/etc/systemd/system/'+name)
def main():
 if os.geteuid()!=0:raise RuntimeError('Administrator access required')
 manifest=json.loads((BUNDLE/'SHA256SUMS.json').read_text())
 for name,digest in manifest.items():
  assert Path(name).name==name and hashlib.sha256((BUNDLE/name).read_bytes()).hexdigest()==digest
 binaries={
  'libvulkan_malisx2.so':['/usr/local/lib/redmi-nas/retroarch/vulkan/libvulkan_malisx2.so','/usr/local/lib/redmi-nas/steam/vulkan/libvulkan_malisx2.so'],
  'libvulkan-retroarch.so.1':['/usr/local/lib/redmi-nas/retroarch/vulkan/libvulkan.so.1'],
  'libvulkan-steam.so.1':['/usr/local/lib/redmi-nas/steam/vulkan/libvulkan.so.1'],
  'udev-host-netlink.so':['/usr/local/lib/redmi-nas/retroarch/udev-host-netlink.so'],
  'x11-bgra.so':['/usr/local/lib/redmi-nas/retroarch/x11-bgra.so'],
  'armsx2_gles_libretro.so':['/usr/local/share/redmi-nas/retroarch/cores/armsx2_gles_libretro.so'],
  'armsx2-official.so':['/usr/local/lib/redmi-nas/retroarch/armsx2-official.so'],
  'genesis_plus_gx_libretro.so':['/usr/local/share/redmi-nas/retroarch/cores/genesis_plus_gx_libretro.so'],
 }
 for name,paths in binaries.items():
  assert name in manifest,'Missing verified native runtime component'
  for path in paths:put(path,(BUNDLE/name).read_bytes(),0o755)
 for app in ['retroarch','steam']:
  p=target('/usr/local/lib/redmi-nas/'+app+'/vulkan/libvulkan.so')
  if p.is_symlink():p.unlink()
  if not p.exists():p.symlink_to('libvulkan.so.1')
 import tarfile
 with tarfile.open(BUNDLE/'armsx2-resources.tar.gz') as archive:
  root=target('/usr/local/share/redmi-nas/retroarch/armsx2-resources')
  for entry in archive:
   if entry.isdir():continue
   p=Path(entry.name)
   if not entry.isfile() or p.is_absolute() or '..' in p.parts:raise RuntimeError('Invalid emulator resource archive')
   destination=root/p;destination.parent.mkdir(parents=True,exist_ok=True)
   with archive.extractfile(entry) as stream:destination.write_bytes(stream.read())
 for name in ['homeio-session.py','gaming_idle_policy.py']:
  source('apps/retroarch/'+name,'/usr/local/lib/redmi-nas/retroarch/'+name,0o755)
 source('apps/retroarch/retroarch-homeio.cfg','/usr/local/lib/redmi-nas/retroarch/retroarch-homeio.cfg')
 for name in ['gaming-app-control.py','gaming-launch-broker.py','steam-webhelper-gpu.sh','repair-program-modes.py','steam-recovery.py','bootstrap-native-steam.py']:
  source('apps/steam/'+name,'/usr/local/lib/redmi-nas/steam/'+name,0o755)
 source('apps/steam/start-steam-gpu','/usr/local/share/redmi-nas/steam/start-steam',0o755)
 source('apps/steam/native-packages.json','/usr/local/share/redmi-nas/steam/native-packages.json')
 source('apps/steam/steam-vulkan-wsi.c','/usr/local/share/redmi-nas/steam/src/steam-vulkan-wsi.c')
 source('apps/steam/gaming-launch-client.py','/usr/local/share/redmi-nas/gaming/gaming-launch-client.py',0o755)
 source('apps/steam/nas-session-branding.js','/usr/local/share/redmi-nas/gaming/nas-session-branding.js')
 for name in ['memory-extension.py','battery-charge.py']:
  source('scripts/lib/'+name,'/usr/local/lib/redmi-nas/'+name,0o755)
 for name in ['quiet-gpu-diagnostics.py','nas-console-verbosity.py']:
  source('scripts/lib/'+name,'/usr/local/lib/redmi-nas/'+name,0o755)
 source('scripts/lib/nas-display-wake.py','/usr/local/libexec/nas-display-wake.py',0o755)
 source('kernel/production/redmi-usb-console-nonblocking.cfg','/etc/systemd/system/serial-getty@ttyGS0.service.d/20-nas-nonblocking-console.conf')
 source('kernel/production/redmi-gpu-boot-completed.cfg','/etc/systemd/system/android_boot_completed.service.d/redmi-gpu-diagnostics.conf')
 source('kernel/production/redmi-console-verbosity.cfg','/etc/systemd/system/nas-cpu-policy.service.d/console-verbosity.conf')
 for name in ['redmi-memory-extension.service','redmi-battery-care.service']:
  source('apps/steam/'+name,'/etc/systemd/system/'+name)
 # Optional features have no enabled marker and no distributed owner state.
 for name in ['redmi-memory-extension.service','redmi-battery-care.service','redmi-steam-trial.service']:
  p=target('/etc/systemd/system/multi-user.target.wants/'+name)
  if p.is_symlink():p.unlink()
 if PREFIX!=Path('/'):
  for name in ['redmi-retroarch-homeio.service','redmi-gaming-launcher.service']:
   p=target('/etc/systemd/system/multi-user.target.wants/'+name)
   if p.is_symlink():p.unlink()
 source('apps/steam/redmi-retroarch-native.service','/etc/systemd/system/redmi-retroarch-native.service')
 source('apps/steam/redmi-gaming-launcher.service','/etc/systemd/system/redmi-gaming-launcher.service')
 unit('redmi-retroarch-homeio.service','''[Unit]
Description=Redmi NAS shared gaming display and Sunshine
After=docker.service
Requires=docker.service
[Service]
Type=simple
ExecStartPre=/usr/bin/docker start retroarch
ExecStart=/usr/local/lib/redmi-nas/retroarch/homeio-session.py --runtime-only
RuntimeDirectory=redmi-gaming
RuntimeDirectoryPreserve=yes
Restart=on-failure
RestartSec=5
TimeoutStopSec=20
KillMode=mixed
[Install]
WantedBy=multi-user.target
''')
 unit('redmi-steam-trial.service','''[Unit]
Description=Native ARM64 Steam Big Picture
After=redmi-retroarch-homeio.service network-online.target
Requires=redmi-retroarch-homeio.service
RequiresMountsFor=/userdata
StartLimitIntervalSec=120
StartLimitBurst=3
[Service]
Type=simple
ExecStart=/usr/local/lib/redmi-nas/steam/enter-session
KillMode=control-group
UMask=0077
TimeoutStopSec=15
MemoryHigh=3584M
MemoryMax=4G
TasksMax=256
RestartForceExitStatus=42
RestartSec=3s
StandardOutput=append:/DATA/AppData/custom-steam/logs/steam-startup.log
StandardError=append:/DATA/AppData/custom-steam/logs/steam-startup.log
[Install]
WantedBy=multi-user.target
''')
 source('apps/steam/enter-session','/usr/local/lib/redmi-nas/steam/enter-session',0o755)
 source('apps/steam/redmi-steam-recover','/usr/local/sbin/redmi-steam-recover',0o755)
 text('/etc/geoclue/conf.d/99-redmi-nas-no-wifi-location.conf','[wifi]\nenable=false\n')
 text('/etc/NetworkManager/conf.d/95-redmi-nas-unused-wifi.conf','[device-redmi-nas-unused-wifi]\nmatch-device=interface-name:wlan1;interface-name:ap0\nmanaged=0\n')
 text('/etc/NetworkManager/conf.d/96-redmi-nas-wifi-powersave.conf','[connection]\nwifi.powersave=2\n')
 source('scripts/lib/homeio-nmcli-cached-list.py','/usr/local/bin/nmcli',0o755)
 text('/usr/local/libexec/redmi-nas/wifi-checksum-compat','''#!/bin/sh
set -eu
[ "${1:-wlan0}" = wlan0 ] || exit 0
[ -e /sys/class/net/wlan0 ] || exit 0
driver=$(readlink -f /sys/class/net/wlan0/device/driver 2>/dev/null || true)
[ "${driver##*/}" = wlan ] || exit 0
/sbin/iwpriv wlan0 set_tcp_csum 0
''',0o755)
 unit('redmi-wifi-checksum-compat.service','''[Unit]
Description=Redmi MediaTek Wi-Fi packet checksum compatibility
After=NetworkManager.service network.target
ConditionPathExists=/sbin/iwpriv
[Service]
Type=oneshot
ExecStart=/usr/local/libexec/redmi-nas/wifi-checksum-compat wlan0
RemainAfterExit=yes
[Install]
WantedBy=multi-user.target
''',enabled=True)
 text('/etc/NetworkManager/dispatcher.d/85-redmi-wifi-checksum','''#!/bin/sh
set -eu
[ "${1:-}" = wlan0 ] || exit 0
case "${2:-}" in up|reapply) /usr/local/libexec/redmi-nas/wifi-checksum-compat wlan0;; esac
''',0o755)
 # Never import a network connection, Bluetooth pairing, account or game profile.
 print(json.dumps({'nativeGamingProgramsStaged':True,'steamClientDownloaded':False,'optionalFeaturesDefaultOff':True,'personalStateCopied':False}))
if __name__=='__main__':main()
