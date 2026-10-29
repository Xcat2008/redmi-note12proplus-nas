#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-only
# Called automatically only after a fresh Homeio/container setup.
set -Eeuo pipefail
test "$EUID" = 0
test "$(uname -m)" = aarch64
case "$(uname -r)" in
  4.19.191-g914ba8403bb3|4.19.191-g914ba8403bb3-dirty) ;;
  *) echo 'The matching tested Redmi kernel is required.' >&2; exit 1 ;;
esac
repo=$(cd "$(dirname "$0")/.." && pwd)
test -f /opt/home-server/.env
test -f /var/lib/redmi-retroarch-homeio/docker-compose.yml
export DEBIAN_FRONTEND=noninteractive NEEDRESTART_MODE=l
apt-get install -y --no-remove --no-install-recommends libgtk2.0-0t64 libdrm2 libgbm1 libx11-6 libxext6 wireless-tools
python3 "$repo/scripts/stage-native-gaming.py"
udevadm control --reload-rules
udevadm trigger --action=change --subsystem-match=misc --sysname-match=uinput
udevadm trigger --action=change --subsystem-match=hidraw
python3 "$repo/scripts/configure-native-gaming-data.py"
runuser -u nas -- /usr/local/lib/redmi-nas/steam/bootstrap-native-steam.py
systemctl daemon-reload
systemd-analyze verify /etc/systemd/system/redmi-steam-trial.service /etc/systemd/system/redmi-gaming-launcher.service /etc/systemd/system/redmi-retroarch-native.service
nginx -t
systemctl reload nginx
systemctl enable --now redmi-retroarch-homeio.service redmi-gaming-launcher.service
systemctl restart redmi-retroarch-homeio.service
echo 'Native Steam and RetroArch profile ready. Both applications start on demand from Homeio or Moonlight.'
