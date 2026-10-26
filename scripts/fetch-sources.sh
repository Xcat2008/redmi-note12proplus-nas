#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-only
set -euo pipefail
task=$(realpath -m "${1:?Usage: fetch-sources.sh BUILD_ROOT}")
repo=$(cd "$(dirname "$0")/.." && pwd)
mkdir -p "$task"
fetch() {
 local name=$1 url=$2 revision=$3
 if [ ! -e "$task/$name" ]; then
  git init -q "$task/$name"
  git -C "$task/$name" remote add origin "$url"
  git -C "$task/$name" fetch --depth=1 origin "$revision"
  git -C "$task/$name" checkout --detach FETCH_HEAD
 fi
 test "$(git -C "$task/$name" rev-parse HEAD)" = "$revision"
}
fetch kernel https://github.com/MiCode/Xiaomi_Kernel_OpenSource.git 914ba8403bb3a957ed37b99dcecdbafce9d16121
fetch mtk-modules https://github.com/MiCode/MTK_kernel_modules.git d854c51c4cab4e54923aa3ac6d67d7348b01346b
fetch wlan-pissarro https://github.com/MiCode/MTK_kernel_modules.git 46b0236ab1116346fcdbaf46d4c70827e7899f12
fetch initramfs-halium-source https://github.com/droidian/initramfs-tools-halium.git a1c2588d25a1f748190027bbc1b8994f290ff32d
patch="$repo/kernel/wlan-ruby-compat.patch"
if git -C "$task/wlan-pissarro" apply --check "$patch"; then
 git -C "$task/wlan-pissarro" apply "$patch"
else
 git -C "$task/wlan-pissarro" apply --reverse --check "$patch"
fi
echo 'Pinned source trees ready. No phone has been accessed or flashed.'
