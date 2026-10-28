#!/usr/bin/python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Restore production debug verbosity after the vendor's engineering boot rule.

Only dynamic pr_debug sites are changed. pr_err/pr_warn and GPU fault paths
are untouched; DMA cache synchronization always runs.
"""
from pathlib import Path
import json,re,os,time
control=next((p for p in (Path('/proc/dynamic_debug/control'),Path('/sys/kernel/debug/dynamic_debug/control')) if p.exists()),None)
targets={'ion_dma_buf_begin_cpu_access':'iommu device, to cache sync','ion_dma_buf_end_cpu_access':'iommu device, to cache sync','mtk_dbgtop_dfd_timeout':'MTK_DBGTOP_LATCH_CTL2'}
def entries():
 result={};vendor_enabled=0
 for line in control.read_text().splitlines():
  m=re.search(r'\]([^ ]+)\s+=([a-z_]+)\s',line)
  if m and m[1] in targets and targets[m[1]] in line:result[m[1]]=m[2]
  if m and 'mediatek' in line.split(':',1)[0] and 'p' in m[2]:vendor_enabled+=1
 return result,vendor_enabled
found,vendor_enabled=entries() if control else ({},0)
vendor_before=vendor_enabled
if set(found)==set(targets):
 # Vendor init reacts asynchronously to sys.boot_completed. Apply after its
 # existing service and verify a short stable interval rather than racing it.
 deadline=time.monotonic()+5;stable_since=None
 while True:
  found,vendor_enabled=entries()
  if vendor_enabled or any('p' in flags for flags in found.values()):
   # Vendor mtklog.rc enables every MediaTek dynamic-debug site on eng and
   # userdebug builds. Keep production verbosity without muting error calls.
   with control.open('w') as f:f.write('file *mediatek* -p\n')
   for function,fragment in targets.items():
    with control.open('w') as f:f.write('func '+function+' format "'+fragment+'" -p\n')
   stable_since=None
  else:
   if stable_since is None:stable_since=time.monotonic()
   if time.monotonic()-stable_since>=1:break
  assert time.monotonic()<deadline,'Routine diagnostic flags did not settle'
  time.sleep(.2)
 found,vendor_enabled=entries();assert all('p' not in flags for flags in found.values()) and vendor_enabled==0
 report={'applied':True,'normal_debug_calls':len(found),'vendor_dynamic_debug_enabled_before':vendor_before,'vendor_dynamic_debug_enabled_after':vendor_enabled,'primary_error_and_warning_calls_unchanged':True}
else:
 # A rollback to the unpatched kernel must not block normal NAS startup.
 report={'applied':False,'reason':'scoped-patched-entries-unavailable','primary_error_and_warning_calls_unchanged':True}
folder=Path('/run/redmi-gaming');folder.mkdir(parents=True,exist_ok=True)
p=folder/'gpu-log-policy.json';temp=p.with_suffix('.new');temp.write_text(json.dumps(report));temp.chmod(0o644);os.replace(temp,p)
print(json.dumps(report))
