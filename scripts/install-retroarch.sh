#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-only
set -Eeuo pipefail
mode=${1:---check}
desktop_user=${2:-nas}
[[ "$mode" == --check || "$mode" == --install || "$mode" == --configure-only ]] || exit 2
[[ "$desktop_user" =~ ^[a-z_][a-z0-9_-]*$ ]] || exit 2
repo=$(cd "$(dirname "$0")/.." && pwd)
prefix=${DESTDIR:-}
if [ -z "$prefix" ]; then
 test "$EUID" = 0
 test "$(uname -m)" = aarch64
 case "$(uname -r)" in
   4.19.191-g914ba8403bb3|4.19.191-g914ba8403bb3-dirty) ;;
   *) echo 'The matching tested Redmi kernel is required.' >&2; exit 1 ;;
 esac
fi
if [ "$mode" = --check ]; then
 echo 'RetroArch preflight passed. No packages or settings changed.'
 exit 0
fi
if [ "$mode" = --install ]; then
 test -z "$prefix" # Offline image builds install their packages inside the image.
 export DEBIAN_FRONTEND=noninteractive NEEDRESTART_MODE=l
 apt-get install -y --no-remove --no-install-recommends \
  retroarch=1.20.0+dfsg-2+b1 retroarch-assets=1.20.0+dfsg-1 \
  libretro-core-info=1.20.0-1 libretro-nestopia libretro-gambatte
fi
install -d -m755 "$prefix/usr/local/bin" "$prefix/usr/local/share/redmi-nas/retroarch/cores" \
 "$prefix/usr/local/share/applications"
install -m755 "$repo/apps/retroarch/redmi-retroarch" "$prefix/usr/local/bin/redmi-retroarch"
install -m644 "$repo/apps/retroarch/retroarch.cfg" "$prefix/usr/local/share/redmi-nas/retroarch/retroarch.cfg"
install -m644 "$repo/apps/retroarch/redmi-retroarch.desktop" "$prefix/usr/local/share/applications/redmi-retroarch.desktop"
archive=${RETROARCH_AUTOCONFIG_ARCHIVE:-}
temporary=
if [ "$mode" = --install ] && [ -z "$archive" ]; then
 temporary=$(mktemp -d)
 trap 'rm -rf -- "$temporary"' EXIT
 archive="$temporary/controllers.tar.gz"
 curl -fL --retry 3 'https://codeload.github.com/libretro/retroarch-joypad-autoconfig/tar.gz/7f94f847057c0829d4e18df27e50930728507f83' -o "$archive"
fi
if [ -n "$archive" ]; then
 test "$(sha256sum "$archive" | cut -d' ' -f1)" = 725fbc7f1e64440d2a44e183769947f2c9d1495b4a9db9ece14a71d972049201
 if [ -z "$temporary" ]; then temporary=$(mktemp -d); trap 'rm -rf -- "$temporary"' EXIT; fi
 mkdir -p "$temporary/controllers"
 tar -xzf "$archive" --strip-components=1 -C "$temporary/controllers"
 install -d -m755 "$prefix/usr/local/share/redmi-nas/retroarch/autoconfig"
 while IFS= read -r -d '' file; do
  relative=${file#"$temporary/controllers/"}
  install -D -m644 "$file" "$prefix/usr/local/share/redmi-nas/retroarch/autoconfig/$relative"
 done < <(find "$temporary/controllers" -type f -name '*.cfg' -print0)
 install -m644 "$temporary/controllers/COPYING" "$prefix/usr/local/share/redmi-nas/retroarch/autoconfig/COPYING"
fi
# Hide the distribution's duplicate launcher, retaining its package and executable.
install -d -m755 "$prefix/usr/local/share/applications"
printf '[Desktop Entry]\nType=Application\nName=RetroArch\nHidden=true\n' > "$prefix/usr/local/share/applications/com.libretro.RetroArch.desktop"
if [ -z "$prefix" ] && mountpoint -q /userdata; then
 install -d -m755 -o "$desktop_user" -g "$(id -gn "$desktop_user")" /DATA/Games
 for name in ROMs BIOS Saves States Screenshots; do
  install -d -m755 -o "$desktop_user" -g "$(id -gn "$desktop_user")" "/DATA/Games/$name"
 done
fi
echo 'RetroArch installed with the native Wayland/GLES profile.'
