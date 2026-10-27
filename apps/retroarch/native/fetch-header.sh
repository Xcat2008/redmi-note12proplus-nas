#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-or-later
set -eu
destination=${1:?Pass an output directory}
mkdir -p "$destination"
url=https://raw.githubusercontent.com/libretro/RetroArch/v1.20.0/libretro-common/include/libretro.h
curl --fail --silent --show-error --location --proto '=https' "$url" -o "$destination/libretro.h"
printf '%s  %s
' 063e295dffaad157216507f58c20d7f5c64a572fc74888502520683d2a453e42 "$destination/libretro.h" | sha256sum -c -
