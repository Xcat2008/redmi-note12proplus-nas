#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-only
set -Eeuo pipefail
test "$EUID" = 0
test "$(uname -m)" = aarch64
case "$(uname -r)" in
  4.19.191-g914ba8403bb3|4.19.191-g914ba8403bb3-dirty) ;;
  *) echo 'The matching tested Redmi kernel is required.' >&2; exit 1 ;;
esac
repo=$(cd "$(dirname "$0")/.." && pwd)
source_dir="$repo/apps/retroarch"
state=/var/lib/redmi-retroarch-homeio
runtime=/usr/local/lib/redmi-nas/retroarch
test -f /opt/home-server/.env
test -x /usr/bin/retroarch
install -d -m755 "$state" "$runtime" /usr/local/share/redmi-nas/gaming
install -m755 "$source_dir/homeio-session.py" "$runtime/homeio-session.py"
install -m644 "$source_dir/retroarch-homeio.cfg" "$runtime/retroarch-homeio.cfg"
install -m644 "$source_dir/redmi-retroarch-homeio.service" /etc/systemd/system/
install -m644 "$source_dir/Dockerfile" /usr/local/share/redmi-nas/gaming/Dockerfile
gcc -O2 -shared -fPIC "$source_dir/x11-bgra.c" -ldl -o "$runtime/x11-bgra.so.new"
chmod 644 "$runtime/x11-bgra.so.new"
mv "$runtime/x11-bgra.so.new" "$runtime/x11-bgra.so"
install -m644 "$source_dir/docker-compose.yml" "$state/docker-compose.yml"
install -m644 "$source_dir/register-homeio.ts" /opt/home-server/nas-register-homeio-gaming.ts
install -d -o nas -g nas -m755 /DATA/AppData/custom-retroarch/native \
 /DATA/AppData/custom-retroarch/config/.config/openbox \
 /DATA/AppData/custom-retroarch/native/playlists
for folder in ROMs BIOS Saves States Screenshots; do
 install -d -o nas -g nas -m755 "/DATA/Games/$folder"
done
install -d -o nas -g nas -m755 /DATA/Games/ROMs/MegaDrive /DATA/Games/ROMs/PS1 \
 /DATA/Media/Filmes /DATA/Media/Series
printf '# Rendering is supervised by redmi-retroarch-homeio.service.\n' \
 > /DATA/AppData/custom-retroarch/config/.config/openbox/autostart
if [ ! -f /DATA/AppData/custom-retroarch/native/retroarch.cfg ]; then
 install -o nas -g nas -m644 "$source_dir/retroarch-homeio.cfg" \
  /DATA/AppData/custom-retroarch/native/retroarch.cfg
fi
install -d -o nas -g nas -m700 /DATA/AppData/custom-retroarch/config/.config/sunshine
if [ ! -f /DATA/AppData/custom-retroarch/config/.config/sunshine/sunshine.conf ]; then
 cat > /DATA/AppData/custom-retroarch/config/.config/sunshine/sunshine.conf <<'CONF'
sunshine_name = Redmi NAS
capture = x11
encoder = software
sw_preset = ultrafast
system_tray = disabled
upnp = disabled
locale = pt
CONF
 chown nas:nas /DATA/AppData/custom-retroarch/config/.config/sunshine/sunshine.conf
 chmod 600 /DATA/AppData/custom-retroarch/config/.config/sunshine/sunshine.conf
fi
# The application is launched through Homeio, not the phone's application grid.
install -d -m755 /usr/local/share/applications
for launcher in redmi-retroarch com.libretro.RetroArch; do
 printf '[Desktop Entry]\nType=Application\nName=RetroArch\nHidden=true\n' \
  > "/usr/local/share/applications/$launcher.desktop"
done
export REDMI_GAMING_SOURCE="$source_dir"
python3 - <<'PY'
from pathlib import Path
import os, re, subprocess
base=Path('/etc/nginx/redmi-retroarch');base.mkdir(exist_ok=True)
icon=next(Path(p) for p in subprocess.check_output(['dpkg','-L','retroarch'],text=True).splitlines()
          if p.endswith('.svg') and ('icon' in p or 'pixmap' in p))
public=Path('/usr/local/share/redmi-nas');public.mkdir(exist_ok=True)
(public/'retroarch-icon.svg').write_bytes(icon.read_bytes())
(base/'homeio-locations.conf').write_text(
 'location = /retroarch-icon.svg { alias /usr/local/share/redmi-nas/retroarch-icon.svg; }\n')
homeio=Path('/etc/nginx/sites-enabled/home-server.conf').resolve(strict=True)
s=homeio.read_text();include='include /etc/nginx/redmi-retroarch/homeio-locations.conf;'
if include not in s:
 if 'server_name _;' not in s: raise RuntimeError('Homeio nginx server not recognized')
 homeio.write_text(s.replace('server_name _;', 'server_name _;\n    '+include,1))
if not (base/'server.key').exists():
 addresses=subprocess.check_output(['hostname','-I'],text=True).split()
 ips=[p for p in addresses if re.fullmatch(r'[0-9]+(?:\.[0-9]+){3}',p)]
 names='DNS:redmi-nas.local,DNS:localhost,IP:127.0.0.1'+''.join(',IP:'+p for p in ips[:1])
 subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-days','825',
  '-keyout',str(base/'server.key'),'-out',str(base/'server.crt'),'-subj','/CN=redmi-nas.local',
  '-addext','subjectAltName='+names],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 (base/'server.key').chmod(0o600)
for port,upstream,title in [(3443,'http://127.0.0.1:3300','RetroArch'),
                             (3444,'https://127.0.0.1:47990','Sunshine')]:
 text='''server {
 listen PORT ssl;
 listen [::]:PORT ssl;
 server_name _;
 error_page 497 =302 https://$host:PORT$request_uri;
 ssl_certificate /etc/nginx/redmi-retroarch/server.crt;
 ssl_certificate_key /etc/nginx/redmi-retroarch/server.key;
 server_tokens off;
 client_max_body_size 1G;
 location = /__homeio_auth {
  internal;
  proxy_pass http://127.0.0.1:12026/api/auth/me;
  proxy_pass_request_body off;
  proxy_set_header Content-Length "";
  proxy_set_header Cookie $http_cookie;
  proxy_set_header Host $host;
 }
 location / {
  auth_request /__homeio_auth;
  error_page 401 = @login;
  proxy_pass UPSTREAM;
  proxy_ssl_verify off;
  proxy_http_version 1.1;
  proxy_set_header Upgrade $http_upgrade;
  proxy_set_header Connection "upgrade";
  proxy_set_header Host $host;
  proxy_set_header Cookie "";
  proxy_read_timeout 3600s;
  proxy_send_timeout 3600s;
  proxy_buffering off;
 }
 location @login {
  default_type text/html;
  return 401 '<!doctype html><html lang="pt"><meta charset="utf-8"><title>TITLE</title><body><h1>TITLE</h1><p>Inicia sess&atilde;o no Homeio para abrir esta aplica&ccedil;&atilde;o.</p></body></html>';
 }
}
'''.replace('PORT',str(port)).replace('UPSTREAM',upstream).replace('TITLE',title)
 target=Path('/etc/nginx/sites-available/redmi-'+title.lower())
 target.write_text(text)
 enabled=Path('/etc/nginx/sites-enabled')/target.name
 if not enabled.exists(): enabled.symlink_to(target)
# The Android uinput group is fixed by this device adaptation, but read it
# rather than assuming the same numeric ID on a reconfigured installation.
compose=Path('/var/lib/redmi-retroarch-homeio/docker-compose.yml')
s=compose.read_text().replace("- '3011'", "- '"+str(Path('/dev/uinput').stat().st_gid)+"'")
compose.write_text(s)
PY
nginx -t
systemctl reload nginx
systemctl daemon-reload
systemctl enable --now redmi-retroarch-homeio.service
cd /opt/home-server
exec node --conditions=react-server --env-file=.env --import tsx \
 nas-register-homeio-gaming.ts "$@"
