#!/bin/bash
set -Eeuo pipefail
test "$(uname -r)" = 4.19.191-g914ba8403bb3
test "$(cat /proc/1/comm)" = systemd
docker info >/dev/null
command -v node >/dev/null || true
test ! -e /opt/home-server
exec > /var/log/nas-homeio-install.log 2>&1
trap 'result=$?; printf "%s\n" "$result" > /var/lib/nas-homeio-install.exit' EXIT
export DEBIAN_FRONTEND=noninteractive NEEDRESTART_MODE=l
export HOMEIO_HOSTNAME=redmi-nas HOMEIO_REPO_BRANCH=v1.10.3
export HOMEIO_PUBLIC_PORT=80 HOMEIO_VERBOSE=true
export NODE_VERSION=22.23.4 GO_VERSION=1.27.3
export NODE_OPTIONS=--max-old-space-size=3072
export GOMAXPROCS=4 MAKEFLAGS=-j4
source "$(dirname "$(readlink -f "$0")")/homeio-reviewed-functions.sh"
require_root
ensure_apt
validate_identifiers
echo NATIVE_PHONE_HOSTNAME
install -d /usr/lib/droidian/device
printf 'redmi-nas\n' > /usr/lib/droidian/device/preferred-hostname
configure_hostname
echo INSTALL_HOMEIO_FEATURE_DEPENDENCIES
apt-get install -y --no-remove --no-install-recommends fswatch gettext-base \
 unar imagemagick ffmpeg ufw fail2ban python3-systemd wsdd2 gdisk parted \
 e2fsprogs exfatprogs
configure_fail2ban_backend
systemctl disable smbd wsdd2 >/dev/null 2>&1 || true
systemctl enable --now avahi-daemon
echo INSTALL_NODE
install_node
echo INSTALL_GO
install_go
echo CLONE_PINNED_HOMEIO_RELEASE
test "${INSTALL_DIR}" = /opt/home-server
test ! -e "${INSTALL_DIR}"
git clone --depth=1 --branch "${REPO_BRANCH}" "${REPO_URL}" "${INSTALL_DIR}"
project_root=$(cd "$(dirname "$(readlink -f "$0")")/../.." && pwd)
cp -a "$project_root/homeio/new-files/." "$INSTALL_DIR/"
git -C "$INSTALL_DIR" apply --check "$project_root/homeio/arm-hardware-reporting.patch"
git -C "$INSTALL_DIR" apply "$project_root/homeio/arm-hardware-reporting.patch"
git -C "$INSTALL_DIR" apply --check "$project_root/homeio/jellyfin-hardware-compat.patch"
git -C "$INSTALL_DIR" apply "$project_root/homeio/jellyfin-hardware-compat.patch"
python3 - "$INSTALL_DIR" <<'PY'
from pathlib import Path
import json, sys
base=Path(sys.argv[1])
p=base/'next.config.mjs';s=p.read_text(encoding='utf-8')
assert 'experimental: {' in s
s=s.replace('experimental: {','experimental: {\n    cpus: 2,',1)
p.write_text(s)
p=base/'package.json';data=json.loads(p.read_text(encoding='utf-8'))
data['scripts']['build']='next build --webpack && npm run build:server'
p.write_text(json.dumps(data,indent=2)+'\n')
PY
ensure_directories
# Retain Droidian's vendor, USB, NetworkManager and logind configuration.
# The generic PC OS overlay is intentionally not deployed on this phone.
echo CREATE_HOMEIO_ENVIRONMENT
create_env_file
chmod 0600 "${ENV_FILE}"
echo CONFIGURE_POSTGRESQL
configure_local_postgres
echo BUILD_HOMEIO
install_homeio
echo BUILD_UPLOAD_SERVICE
build_upload_server
install_systemd_service
install_upload_server_service
install_reverse_proxy
install_dbus_helper_service
echo HOMEIO_INSTALLED
systemctl is-active home-server home-server-upload home-server-dbus nginx postgresql docker
curl -fsS -o /var/lib/nas-homeio-first-page.html -w 'HOMEIO_HTTP_STATUS=%{http_code}\n' http://127.0.0.1/
df -h / /DATA
