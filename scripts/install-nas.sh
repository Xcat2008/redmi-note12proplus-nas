#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-only
# NAS software setup only. Never unlocks, flashes or formats a phone.
set -Eeuo pipefail
mode=${1:---check}
desktop_user=${2:-}
[[ "$mode" == --check || "$mode" == --install ]] || { echo 'Usage: install-nas.sh --check|--install DESKTOP_USER' >&2; exit 2; }
[[ "$desktop_user" =~ ^[a-z_][a-z0-9_-]*$ ]] || { echo 'Specify your Linux desktop user.' >&2; exit 2; }
test "$EUID" = 0 || { echo 'Run with sudo.' >&2; exit 1; }
test "$(uname -m)" = aarch64
test "$(uname -r)" = 4.19.191-g914ba8403bb3
test "$(cat /proc/1/comm)" = systemd
grep -q '^13[.]' /etc/debian_version
mountpoint -q /userdata
test "$(readlink -f /DATA)" = /userdata/DATA
test -d /userdata/DATA
desktop_uid=$(id -u "$desktop_user")
test -S "/run/user/$desktop_uid/bus"
repo=$(cd "$(dirname "$0")/.." && pwd)
test -f "${REDMI_NAS_HARDWARE_BUNDLE:-/usr/share/redmi-nas-hardware}/SHA256SUMS" || {
 echo 'The matching hardware bundle is required. See apps/jellyfin/mediatek/full/README.md.' >&2
 exit 1
}
echo 'Preflight: correct ARM64 native kernel, Debian base, data mount and desktop session.'
if [ -e /opt/home-server ]; then
 echo 'Homeio is already installed. This installer will not overwrite it.'
 test "$mode" = --check && exit 0
 exit 1
fi
if [ "$mode" = --check ]; then
 echo 'Fresh-system preflight passed. No files or services changed.'
 exit 0
fi
test ! -e /etc/docker/daemon.json || { echo 'Review existing Docker configuration manually.' >&2; exit 1; }
for location in /var/lib/docker /var/lib/containerd; do
 if [ -L "$location" ]; then
  test "$(readlink -f "$location")" = "/userdata/$(basename "$location")"
 elif [ -e "$location" ]; then
  echo "Existing $location needs a reviewed storage migration; refusing to overwrite it." >&2
  exit 1
 fi
done
export DEBIAN_FRONTEND=noninteractive NEEDRESTART_MODE=l
apt-get update
apt-get install -y --no-remove --no-install-recommends postgresql-common
apt-get install -y --no-remove --no-install-recommends ca-certificates curl gnupg git jq rsync python3 python3-gi build-essential libudev-dev tar xz-utils unzip procps postgresql postgresql-contrib openssl nginx samba smbclient cifs-utils avahi-daemon libnss-mdns
install -d -m755 /etc/apt/keyrings /etc/docker /userdata/docker /userdata/containerd
curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
cat > /etc/apt/sources.list.d/redmi-nas-docker.sources <<'EOF'
Types: deb
URIs: https://download.docker.com/linux/debian
Suites: trixie
Components: stable
Architectures: arm64
Signed-By: /etc/apt/keyrings/docker.asc
EOF
for location in /var/lib/docker /var/lib/containerd; do
 test -L "$location" || ln -s "/userdata/$(basename "$location")" "$location"
done
cat > /etc/docker/daemon.json <<'EOF'
{
  "data-root": "/userdata/docker",
  "storage-driver": "overlay2",
  "features": {"containerd-snapshotter": false},
  "log-driver": "local",
  "log-opts": {"max-size": "10m", "max-file": "3"}
}
EOF
apt-get update
apt-get install -y --no-remove --no-install-recommends \
 'docker-ce=5:29.9.2-1~debian.13~trixie' \
 'docker-ce-cli=5:29.9.2-1~debian.13~trixie' \
 'containerd.io=2.4.2-3~debian.13~trixie' \
 'docker-buildx-plugin=0.38.1-1~debian.13~trixie' \
 'docker-compose-plugin=5.6.1-1~debian.13~trixie'
systemctl enable --now docker
docker run --rm hello-world
bash "$repo/scripts/install-energy-profiles.sh"
bash "$repo/scripts/install-phone-adaptations.sh" "$desktop_user"
bash "$repo/scripts/install-mediatek-video.sh"
bash "$repo/scripts/install-hardware-services.sh"
bash "$repo/scripts/install-retroarch.sh" --install "$desktop_user"
bash "$repo/homeio/installer/install-homeio-native-phone.sh"
bash "$repo/scripts/install-homeio-gaming.sh"
bash "$repo/scripts/install-native-gaming.sh"
echo 'NAS setup finished. Open http://redmi-nas.local and create your Homeio account.'
