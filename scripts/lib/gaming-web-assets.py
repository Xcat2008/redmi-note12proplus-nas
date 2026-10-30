#!/usr/bin/python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Install the complete browser launch page and Homeio shortcut routes."""
from pathlib import Path
import argparse,re

START='# BEGIN redmi-gaming-web-assets'
END='# END redmi-gaming-web-assets'
BLOCK='''# BEGIN redmi-gaming-web-assets
location = /gaming-launcher.html { alias /usr/local/share/redmi-nas/gaming-launcher.html; }
location = /gaming-launcher.js { alias /usr/local/share/redmi-nas/gaming-launcher.js; }
location = /sunshine { return 302 https://$host:3444/; }
location = /sunshine/ { return 302 https://$host:3444/; }
# END redmi-gaming-web-assets
'''

def install(root,public):
    root=Path(root).resolve();public=Path(public).resolve()
    assets={name:(public/name).read_bytes() for name in ['gaming-launcher.html','gaming-launcher.js']}
    html=assets['gaming-launcher.html'].decode('utf-8')
    if '/gaming-launcher.js' not in html or any(f'id="{name}"' not in html for name in ['title','status','error','start','stream']):
        raise ValueError('Incomplete browser launch document')
    config=root/'etc/nginx/redmi-retroarch/homeio-locations.conf'
    old=config.read_text(encoding='utf-8')
    if START in old:
        if old.count(START)!=1 or old.count(END)!=1:raise ValueError('Unknown existing route block')
        text=re.sub(re.escape(START)+r'.*?'+re.escape(END),BLOCK.strip(),old,flags=re.S)
    else:
        if any('location = '+path in old for path in ['/gaming-launcher.html','/gaming-launcher.js','/sunshine']):
            raise ValueError('Existing shortcut routes need review before replacement')
        text=old.rstrip()+'\n\n'+BLOCK
    target=root/'usr/local/share/redmi-nas';target.mkdir(parents=True,exist_ok=True)
    for name,data in assets.items():
        path=target/name
        if path.is_symlink():raise ValueError('Unexpected asset symlink')
        path.write_bytes(data);path.chmod(0o644)
    config.write_text(text,encoding='utf-8')
    return ['gaming-launcher.html','gaming-launcher.js','/sunshine/']

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,default=Path('/'));parser.add_argument('--public',type=Path,required=True)
    args=parser.parse_args();install(args.root,args.public)
