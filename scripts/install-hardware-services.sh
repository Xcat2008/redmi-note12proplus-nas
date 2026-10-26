#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-only
set -Eeuo pipefail
repo=$(cd "$(dirname "$0")/.." && pwd)
prefix=${DESTDIR:-}
bundle=${REDMI_NAS_HARDWARE_BUNDLE:-$prefix/usr/share/redmi-nas-hardware}
if [ -z "$prefix" ]; then
 test "$EUID" = 0
 test "$(uname -r)" = 4.19.191-g914ba8403bb3
fi
python3 - "$repo/hardware/runtime-lock.json" "$bundle" <<'PY'
import hashlib,json,sys
from pathlib import Path
lock=json.loads(Path(sys.argv[1]).read_text());bundle=Path(sys.argv[2])
for name,digest in lock['files'].items():
 path=bundle/name
 if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:
  raise SystemExit('Missing or mismatched hardware bundle file: '+name)
print('Hardware bundle checksums verified')
PY
video="$prefix/usr/local/lib/redmi-nas/mediatek"
module="$prefix/lib/modules/4.19.191-g914ba8403bb3/extra"
install -d -m755 "$video/run" "$module" "$prefix/usr/local/sbin" \
 "$prefix/etc/modules-load.d" "$prefix/etc/sysctl.d" \
 "$prefix/etc/systemd/system/bluebinder.service.d" \
 "$prefix/etc/systemd/system/graphical.target.wants" \
 "$prefix/etc/systemd/system/bluetooth.target.wants" \
 "$prefix/etc/systemd/system/multi-user.target.wants"
for file in surface-transcode ffmpeg-bridge; do
 install -m755 "$bundle/$file" "$video/$file.new"
 mv "$video/$file.new" "$video/$file"
done
install -m755 "$bundle/bluebinder-nas" "$prefix/usr/local/sbin/bluebinder-nas.new"
mv "$prefix/usr/local/sbin/bluebinder-nas.new" "$prefix/usr/local/sbin/bluebinder-nas"
install -m644 "$bundle/hci_vhci.ko" "$bundle/hidp.ko" "$module/"
install -m644 "$bundle/modules.builtin" "$bundle/modules.builtin.modinfo" "$prefix/lib/modules/4.19.191-g914ba8403bb3/"
printf 'extra/hci_vhci.ko\nextra/hidp.ko\n' > "$prefix/lib/modules/4.19.191-g914ba8403bb3/modules.order"
install -m755 "$repo/apps/jellyfin/mediatek/full/broker.py" "$video/broker.py"
install -m755 "$repo/apps/jellyfin/mediatek/full/prepare-video-services" "$video/prepare-video-services"
install -m644 "$repo/apps/jellyfin/mediatek/full/redmi-video-broker.service" "$prefix/etc/systemd/system/redmi-video-broker.service"
printf 'hci_vhci\nhidp\n' > "$prefix/etc/modules-load.d/redmi-bluetooth.conf"
printf '# Android 32-bit vendor services require thread IDs below 65536.\nkernel.pid_max = 65535\n' > "$prefix/etc/sysctl.d/70-redmi-android-pids.conf"
cat > "$prefix/etc/systemd/system/bluebinder.service.d/90-redmi-nas.conf" <<'EOF'
[Unit]
After=systemd-modules-load.service

[Service]
ExecStart=
ExecStart=/usr/local/sbin/bluebinder-nas
# The stock post hook assumes rfkill and an Android Bluetooth-address property.
# This port receives the real controller address directly from the vendor HAL.
ExecStartPost=
Environment=BLUEBINDER_LOCAL_EXT_FEATURES_PAGE_2_MASK=0400000000000000
EOF
ln -sfn /usr/lib/systemd/system/bluebinder.service "$prefix/etc/systemd/system/graphical.target.wants/bluebinder.service"
ln -sfn /usr/lib/systemd/system/bluetooth.service "$prefix/etc/systemd/system/bluetooth.target.wants/bluetooth.service"
ln -sfn /etc/systemd/system/redmi-video-broker.service "$prefix/etc/systemd/system/multi-user.target.wants/redmi-video-broker.service"
printf '#!/bin/sh\nexec /mediatek/ffmpeg-bridge "$@"\n' > "$video/ffmpeg.new"
chmod 755 "$video/ffmpeg.new"
mv "$video/ffmpeg.new" "$video/ffmpeg"
if [ -z "$prefix" ]; then
 sysctl -w kernel.pid_max=65535
 depmod -a
 modprobe hci_vhci
 modprobe hidp
 systemctl daemon-reload
 systemctl restart redmi-video-broker
 systemctl restart --no-block bluebinder
fi
echo 'Hardware video and Bluetooth services installed.'
