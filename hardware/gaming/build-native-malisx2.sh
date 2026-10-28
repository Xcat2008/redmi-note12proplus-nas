#!/bin/bash
set -euo pipefail
base=/opt/redmi-native-build
export PATH="$base/native-driver-tools/bin:$HOME/.cargo/bin:$PATH"
export LIBCLANG_PATH=/usr/lib/llvm-14/lib
meson setup "$base/malisx2-native-build" "$base/malisx2-trial-source" --cross-file /opt/redmi-native-build/recipes/malisx2-linux-aarch64.ini --buildtype=release >"$base/malisx2-native-configure.log" 2>&1
ninja -C "$base/malisx2-native-build" -j6 src/libvulkan_malisx2.so >"$base/malisx2-native-compile.log" 2>&1
file "$base/malisx2-native-build/src/libvulkan_malisx2.so"
