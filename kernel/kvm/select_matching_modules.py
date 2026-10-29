#!/usr/bin/python3
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 José Miranda (Xcat2008)
"""Select matching phone modules before Android starts, without replacing originals."""
from pathlib import Path
import hashlib,json,os,subprocess


def select(root=Path('/'),release=None,mount=None):
    release=release or os.uname().release
    mount=mount or (lambda source,target:subprocess.run(['mount','--bind',str(source),str(target)],check=True))
    bundle=root/'usr/local/lib/redmi-nas/kvm-kernel'
    manifest=json.loads((bundle/'manifest.json').read_text())
    state=dict(kernelRelease=release,matchingRelease=manifest['kernelRelease'],bindMounts=[],deferredTargets=[])
    if release==manifest['kernelRelease']:
        for item in manifest['vendorBindings']:
            source=bundle/'modules'/item['module']
            if not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest()!=item['sha256']:
                raise ValueError('Missing or mismatched kernel module: '+item['module'])
            targets=[(root/item['target'].lstrip('/'),item['module']!='binfmt_misc.ko')]
            if item['module']!='binfmt_misc.ko':
                targets.extend((root/path/item['module'],False) for path in ['vendor/lib/modules','var/lib/lxc/android/rootfs/vendor/lib/modules'])
            for target,required in targets:
                if not target.is_file():
                    if required:raise ValueError('Missing vendor overlay target: '+item['module'])
                    # Steam may not be installed yet; Android's mount aliases
                    # may not exist until LXC has prepared its own rootfs.
                    state['deferredTargets'].append(target.relative_to(root).as_posix())
                    continue
                if hashlib.sha256(target.read_bytes()).hexdigest()!=item['sha256']:mount(source,target)
                if hashlib.sha256(target.read_bytes()).hexdigest()!=item['sha256']:
                    raise ValueError('Kernel module bind verification failed: '+item['module'])
                state['bindMounts'].append(target.relative_to(root).as_posix())
        state['selection']='kvm-version-matched-modules'
    else:state['selection']='original-module-files-retained'
    output=root/'var/lib/redmi-nas/kvm-module-selection.json'
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(state,indent=2)+'\n')
    return state


if __name__=='__main__':print(json.dumps(select()))
