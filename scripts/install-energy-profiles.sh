#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-only
set -Eeuo pipefail
repo=$(cd "$(dirname "$0")/.." && pwd)
prefix=${DESTDIR:-}
source_dir="$repo/hardware/power"
target="$prefix/usr/local/libexec/redmi-nas"
if [ -z "$prefix" ]; then
    test "$EUID" = 0
    test "$(uname -m)" = aarch64
    case "$(uname -r)" in
      4.19.191-g914ba8403bb3|4.19.191-g914ba8403bb3-dirty) ;;
      *) echo 'The matching tested Redmi kernel is required.' >&2; exit 1 ;;
    esac
fi
test -f "$prefix/usr/share/mps/mps.gresource"
python3 - "$source_dir" <<'PY'
from pathlib import Path
import hashlib,json,sys
p=Path(sys.argv[1]);lock=json.loads((p/'source-lock.json').read_text())
assert hashlib.sha256((p/'mobile-power-saver-nas.patch').read_bytes()).hexdigest()==lock['patch_sha256']
PY
binary=${REDMI_NAS_MPS_BINARY:-}
if [ -z "$binary" ] && [ -f "$target/mobile-power-saver" ]; then
    expected=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["tested_binary_sha256"])' "$source_dir/source-lock.json")
    if [ "$(sha256sum "$target/mobile-power-saver" | cut -d' ' -f1)" = "$expected" ]; then binary="$target/mobile-power-saver"; fi
fi
if [ -n "$binary" ]; then
    expected=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["tested_binary_sha256"])' "$source_dir/source-lock.json")
    echo "$expected  $binary" | sha256sum --check --status
else
    test -z "$prefix" || { echo 'Offline image installation requires the tested ARM64 binary.' >&2; exit 1; }
    export DEBIAN_FRONTEND=noninteractive
    apt-get install -y --no-remove --no-install-recommends build-essential pkg-config libglib2.0-dev libnl-3-dev libnl-genl-3-dev ca-certificates curl python3 git
    build=$(mktemp -d /var/tmp/redmi-nas-power.XXXXXXXX)
    trap 'rm -rf -- "$build"' EXIT
    url=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["archive_url"])' "$source_dir/source-lock.json")
    digest=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["archive_sha256"])' "$source_dir/source-lock.json")
    curl -fL --retry 3 "$url" -o "$build/source.tar.gz"
    echo "$digest  $build/source.tar.gz" | sha256sum --check --status
    mkdir "$build/source"
    tar -xzf "$build/source.tar.gz" --strip-components=1 -C "$build/source"
    git -C "$build/source" apply --check "$source_dir/mobile-power-saver-nas.patch"
    git -C "$build/source" apply "$source_dir/mobile-power-saver-nas.patch"
    cat > "$build/source/config.h" <<'EOF'
#define APP_ID "org.adishatz.Mps"
#define PACKAGE_VERSION "0.9.7-redmi-nas1"
#define MPS_RESOURCES "/usr/share/mps/mps.gresource"
#define GETTEXT_PACKAGE "mps"
#define LOCALEDIR "/usr/share/locale"
#define WIFI_ENABLED 1
EOF
    (
        cd "$build/source"
        cc -O2 -fstack-protector-strong -ffile-prefix-map="$PWD"=/usr/src/redmi-nas-mobile-power-saver \
            -I. -Isystem system/bus.c system/cpufreq.c system/cpufreq_device.c system/devfreq.c \
            system/devfreq_device.c system/processes.c system/freq_device.c system/kernel_settings.c \
            system/logind.c system/main.c system/manager.c system/wifi.c common/services.c common/utils.c \
            $(pkg-config --cflags --libs glib-2.0 gio-2.0 gio-unix-2.0 libnl-genl-3.0) -o mobile-power-saver-nas
        strip mobile-power-saver-nas
    )
    binary="$build/source/mobile-power-saver-nas"
fi
python3 - "$binary" <<'PY'
from pathlib import Path
import sys
b=Path(sys.argv[1]).read_bytes()
assert b[:4]==b'\x7fELF' and int.from_bytes(b[18:20],'little')==183
PY
install -d "$target" "$prefix/usr/local/share/dbus-1/system-services" "$prefix/usr/local/share/redmi-nas/power" "$prefix/etc/systemd/system" "$prefix/etc/homeio"
if [ "$(readlink -f "$binary")" != "$(readlink -f "$target/mobile-power-saver" 2>/dev/null || true)" ]; then
    install -m755 "$binary" "$target/mobile-power-saver"
fi
install -m755 "$source_dir/mps-launch" "$target/mps-launch"
install -m644 "$source_dir/source-lock.json" "$source_dir/mobile-power-saver-nas.patch" "$source_dir/COPYING.mobile-power-saver" "$prefix/usr/local/share/redmi-nas/power/"
cat > "$prefix/usr/local/share/dbus-1/system-services/org.adishatz.Mps.service" <<'EOF'
[D-BUS Service]
Name=org.adishatz.Mps
Exec=/usr/local/libexec/redmi-nas/mps-launch
User=root
EOF
install -m755 "$repo/scripts/lib/nas-cpu-policy.sh" "$prefix/usr/local/libexec/nas-cpu-policy.sh"
install -m755 "$repo/scripts/lib/nas-cpu-online.py" "$prefix/usr/local/libexec/nas-cpu-online.py"
install -m644 "$repo/scripts/lib/nas-cpu-policy.service" "$prefix/etc/systemd/system/nas-cpu-policy.service"
printf 'redmi-ruby-nas\n' > "$prefix/etc/homeio/hardware-profile"
if [ -z "$prefix" ]; then
    busctl --system call org.freedesktop.DBus /org/freedesktop/DBus org.freedesktop.DBus ReloadConfig
    systemctl daemon-reload
    systemctl enable nas-cpu-policy.service
    old=$(busctl --system call org.freedesktop.DBus /org/freedesktop/DBus org.freedesktop.DBus GetConnectionUnixProcessID s org.adishatz.Mps 2>/dev/null | awk '{print $2}' || true)
    if [[ "$old" =~ ^[0-9]+$ ]]; then
        executable=$(readlink -f "/proc/$old/exe")
        if [ "$executable" != "$target/mobile-power-saver" ]; then
            case "$executable" in /usr/sbin/mobile-power-saver|"$target/mobile-power-saver (deleted)") ;; *) echo 'Unexpected power service executable; refusing to interrupt it.' >&2; exit 1 ;; esac
            kill -INT "$old"
            for ignored in $(seq 1 30); do kill -0 "$old" 2>/dev/null || break; sleep 0.2; done
        fi
    fi
    busctl --system call org.adishatz.Mps /org/adishatz/Mps org.freedesktop.DBus.Peer Ping
    busctl --system get-property org.freedesktop.UPower.PowerProfiles /org/freedesktop/UPower/PowerProfiles org.freedesktop.UPower.PowerProfiles Version | grep -q redmi-nas1
    systemctl restart nas-cpu-policy.service
else
    install -d "$prefix/etc/systemd/system/multi-user.target.wants"
    ln -sfn /etc/systemd/system/nas-cpu-policy.service "$prefix/etc/systemd/system/multi-user.target.wants/nas-cpu-policy.service"
fi
echo 'CPU profiles retain factory frequency limits, GPU/memory DVFS and thermal protection.'
