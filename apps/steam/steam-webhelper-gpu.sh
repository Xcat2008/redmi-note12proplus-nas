#!/bin/sh
set -eu
cd /DATA/AppData/custom-steam/native-arm64/home/.local/share/Steam/steamrtarm64
disabled=""
for arg in "$@"; do
    case "$arg" in --disable-features=*) disabled=${arg#--disable-features=};; esac
done
# Chromium's native Vulkan renderer and ANGLE's Vulkan GL backend are distinct.
# The Mali bridge supports GLES2; keep Chromium's raster/compositor on that API.
# The GPU process needs direct access to the existing vendor device interfaces.
# Renderer sandboxing remains enabled.
# Rasterize vector UI on the CPU: the forced GPU raster path corrupted icons.
# ANGLE Vulkan GPU composition remains enabled.
exec ./steamwebhelper "$@" \
    --use-gl=angle --use-angle=vulkan \
    --disable-features="${disabled:+$disabled,}Vulkan,UseSkiaRenderer,CanvasOopRasterization" \
    --use-cmd-decoder=passthrough --disable-es3-gl-context \
    --disable-gpu-rasterization --disable-oop-rasterization \
    --ozone-platform=x11 --disable-gpu-sandbox
