#!/usr/bin/python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Make the tested NAS CPU clusters available without overriding safety policies."""
from pathlib import Path
import argparse,json,platform,re

KERNELS={'4.19.191-g914ba8403bb3','4.19.191-g914ba8403bb3-dirty'}

def restore(root:Path,kernel:str,profile:str):
 result={'activated':[],'profile':profile,'thermalControlsModified':False}
 if kernel not in KERNELS or profile not in {'balanced','performance'}:
  return {**result,'reason':'profile-not-requesting-all-cores'}
 for name,field in [('thermal_limit','PPM thermal activate'),('dlpt_limit','PPM DLPT activate')]:
  try:value=(root/'proc/ppm/policy'/name).read_text()
  except OSError:return {**result,'reason':'platform-safety-state-unavailable'}
  if not re.search(r'^'+re.escape(field)+r'\s*=\s*0\s*$',value,re.M):
   return {**result,'reason':'platform-safety-limit-active'}
 for cpu in (6,7):
  node=root/f'sys/devices/system/cpu/cpu{cpu}/online'
  try:
   if node.read_text().strip()=='0':
    node.write_text('1\n')
    if node.read_text().strip()=='1':result['activated'].append(cpu)
  except OSError:
   # The kernel can refuse a hotplug request; never disable its policy to force it.
   return {**result,'reason':'kernel-refused-core-activation'}
 return {**result,'reason':'available'}

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--profile',choices=['balanced','performance','power-saver'],required=True)
 args=parser.parse_args();print(json.dumps(restore(Path('/'),platform.release(),args.profile)))
