#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-or-later
set -eu
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
repo=$(CDPATH= cd -- "$here/../../.." && pwd)
output=${1:-"$repo/build/native-adapters"}
mkdir -p "$output"
sh "$here/fetch-header.sh" "$output"
cc=${CC:-cc}
"$cc" -O2 -Wall -Wextra -Werror -shared -fPIC -I"$output" -ffile-prefix-map="$repo"=redmi-nas-source "$here/libretro-adapter.c" -ldl -o "$output/armsx2_gles_libretro.so"
"$cc" -O2 -Wall -Wextra -Werror -shared -fPIC -Wl,-Bsymbolic -ffile-prefix-map="$repo"=redmi-nas-source "$here/vulkan-x11-bridge.c" -lX11 -lXext -ldl -o "$output/libvulkan.so.1"
printf 'Adapters built in %s. Nothing has been installed.
' "$output"
