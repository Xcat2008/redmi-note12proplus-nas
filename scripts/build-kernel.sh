#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-only
set -euo pipefail
task=$(realpath "${1:?Usage: build-kernel.sh BUILD_ROOT}")
repo=$(cd "$(dirname "$0")/.." && pwd)
test "$(git -C "$task/kernel" rev-parse HEAD)" = 914ba8403bb3a957ed37b99dcecdbafce9d16121
test -x "$task/toolchains/clang-r383902/bin/clang"
export PATH="$task/toolchains/clang-r383902/bin:$PATH"
export LD_LIBRARY_PATH="$task/toolchains/clang-r383902/lib64${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
mkdir -p "$task/linux-output"
test ! -e "$task/linux-output/.config" || { echo 'Existing config retained; choose a fresh BUILD_ROOT for the packaged config.' >&2; exit 1; }
cp "$repo/kernel/linux-resolved.config" "$task/linux-output/.config"
base=(make -C "$task/kernel" "O=$task/linux-output" ARCH=arm64 LLVM=1 LLVM_IAS=1
 CROSS_COMPILE=aarch64-linux-gnu- CROSS_COMPILE_COMPAT=arm-linux-gnueabi-
 CLANG_TRIPLE=aarch64-linux-gnu- CC=clang LD=ld.lld AR=llvm-ar NM=llvm-nm
 OBJCOPY=llvm-objcopy OBJDUMP=llvm-objdump READELF=llvm-readelf STRIP=llvm-strip HOSTCC=gcc HOSTCXX=g++)
"${base[@]}" olddefconfig
"${base[@]}" -j"${JOBS:-4}" Image.gz
sha256sum "$task/linux-output/arch/arm64/boot/Image.gz"
echo 'Kernel compiled on the workstation. This is not a complete or flashed ROM.'
