#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-only
set -euo pipefail
test "$EUID" = 0 || { echo 'Run with sudo.' >&2; exit 1; }
desktop_user=${1:?Usage: sudo bash install-phone-adaptations.sh DESKTOP_USER}
[[ $desktop_user =~ ^[a-z_][a-z0-9_-]*$ ]] || exit 1
desktop_uid=$(id -u "$desktop_user")
case "$(uname -r)" in
  4.19.191-g914ba8403bb3|4.19.191-g914ba8403bb3-dirty) ;;
  *) echo 'The matching tested Redmi kernel is required.' >&2; exit 1 ;;
esac
test -S "/run/user/$desktop_uid/bus" || { echo 'Start the Phosh user session first.' >&2; exit 1; }
repo=$(cd "$(dirname "$0")/.." && pwd)
backup="/var/backups/redmi-nas/$(date -u +%Y%m%dT%H%M%SZ)-$$"
mkdir -p "$backup" /usr/local/libexec /etc/homeio
usercmd=(runuser -u "$desktop_user" -- env "XDG_RUNTIME_DIR=/run/user/$desktop_uid" "DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$desktop_uid/bus")
for scope in /org/adishatz/Mps/ /org/gnome/desktop/session/ /org/gnome/settings-daemon/plugins/power/; do
 "${usercmd[@]}" dconf dump "$scope" > "$backup/$(echo "$scope" | tr / _).dconf"
done
for unit in sleep.target suspend.target hibernate.target hybrid-sleep.target; do
 printf '%s ' "$unit" >> "$backup/sleep-targets.txt"
 systemctl is-enabled "$unit" >> "$backup/sleep-targets.txt" 2>&1 || true
done
for file in /etc/default/redmi-nas /etc/homeio/hardware-profile /usr/local/libexec/nas-display-wake.py /usr/local/libexec/nas-cpu-policy.sh /etc/systemd/system/nas-display-wake.service /etc/systemd/system/nas-cpu-policy.service; do
 test ! -e "$file" || cp --parents "$file" "$backup/"
done
"${usercmd[@]}" gsettings set org.adishatz.Mps screen-off-power-saving false
"${usercmd[@]}" gsettings set org.adishatz.Mps suspend-services false
"${usercmd[@]}" gsettings set org.gnome.desktop.session idle-delay 15
"${usercmd[@]}" gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-ac-type nothing
"${usercmd[@]}" gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-battery-type nothing
install -m755 "$repo/scripts/lib/nas-display-wake.py" /usr/local/libexec/nas-display-wake.py
install -m755 "$repo/scripts/lib/nas-cpu-policy.sh" /usr/local/libexec/nas-cpu-policy.sh
install -m644 "$repo/scripts/lib/nas-display-wake.service" /etc/systemd/system/nas-display-wake.service
install -m644 "$repo/scripts/lib/nas-cpu-policy.service" /etc/systemd/system/nas-cpu-policy.service
printf 'NAS_DESKTOP_USER=%s
' "$desktop_user" > /etc/default/redmi-nas
printf 'redmi-ruby-nas
' > /etc/homeio/hardware-profile
systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target
systemctl daemon-reload
systemctl enable --now nas-display-wake.service nas-cpu-policy.service
echo "Adaptations installed. Previous settings/files: $backup"
echo 'The profile enables the separate Homeio Jellyfin compatibility patch when installed.'
