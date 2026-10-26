#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-only
set -Eeuo pipefail
repo=$(cd "$(dirname "$0")/.." && pwd)
source_dir="$repo/apps/jellyfin/mediatek"
prefix=${DESTDIR:-}
if [ -z "$prefix" ]; then
 test "$EUID" = 0
 test "$(uname -m)" = aarch64
 test "$(uname -r)" = 4.19.191-g914ba8403bb3
fi
target="$prefix/usr/local/lib/redmi-nas/mediatek"
install -d -m755 "$target/init" "$prefix/etc/homeio"
"${CC:-cc}" -shared -fPIC -O2 -Wall -Wextra -Werror  -ffile-prefix-map="$repo"=/usr/src/redmi-nas  -o "$target/libmediatek-dmabuf.so.new" "$source_dir/mediatek-dmabuf-bridge.c" -ldl -pthread
chmod 644 "$target/libmediatek-dmabuf.so.new"
mv "$target/libmediatek-dmabuf.so.new" "$target/libmediatek-dmabuf.so"
install -m644 "$source_dir/mediatek-dmabuf-bridge.c" "$target/mediatek-dmabuf-bridge.c"
install -m755 "$source_dir/ffmpeg" "$target/ffmpeg"
install -m755 "$source_dir/init/50-redmi-mediatek.sh" "$target/init/50-redmi-mediatek.sh"
ln -sfn /usr/lib/jellyfin-ffmpeg/ffprobe "$target/ffprobe"
printf 'redmi-ruby-nas\n' > "$prefix/etc/homeio/hardware-profile"
printf 'mediatek-ion-v4l2-h264-v1\n' > "$prefix/etc/homeio/mediatek-video-profile"
echo 'MediaTek adapter installed for the Homeio Jellyfin profile.'
