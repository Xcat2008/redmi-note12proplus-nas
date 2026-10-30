#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-only
set -Eeuo pipefail
repo=$(cd "$(dirname "$0")/.." && pwd)
prefix=${DESTDIR:-}
if [ -z "$prefix" ]; then
 test "$EUID" = 0
 test "$(uname -m)" = aarch64
 case "$(uname -r)" in
  4.19.191-g914ba8403bb3|4.19.191-g914ba8403bb3-dirty) ;;
  *) echo 'The tested Redmi kernel is required.' >&2; exit 1 ;;
 esac
 test -c /dev/video2
 test -c /dev/ion
fi
source_dir="$repo/apps/retroarch"
target="$prefix/usr/local/lib/redmi-nas/selkies"
install -d -m755 "$target"
"${CC:-cc}" -shared -fPIC -O2 -Wall -Wextra -Werror \
 -ffile-prefix-map="$repo"=/usr/src/redmi-nas \
 -o "$target/libmediatek-pixelflux.so.new" "$source_dir/mediatek-pixelflux.c" -ldl -pthread
chmod 644 "$target/libmediatek-pixelflux.so.new"
mv "$target/libmediatek-pixelflux.so.new" "$target/libmediatek-pixelflux.so"
echo 'MediaTek Selkies adapter installed. No running session was restarted.'
