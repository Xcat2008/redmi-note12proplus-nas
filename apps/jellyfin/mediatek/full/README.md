# Hardware decode, resize and encode

This bridge connects the container's FFmpeg invocation to the Android media services already supplied by Droidian. Compressed video is decoded by a named MediaTek Codec2 component. The resulting hardware buffer is imported into EGL, resized by a Mali OpenGL ES shader and submitted to the MediaTek H.264 encoder. Native fences release buffers after GPU work completes.

The broker accepts a read-only file descriptor over a local Unix socket. It enters the existing Android mount/PID namespaces without modifying media ownership or permissions. The container receives no Android binder devices, host process namespace or privileged mode. Numeric parameters are bounded and concurrent sessions are limited. The broker has no network listener.

The native transport writer preserves the codec's presentation timestamps. FFmpeg copies that video into Jellyfin's HLS output and handles the original audio track. Audio conversion, container processing, application services and unsupported video paths can still use the CPU.

Validated inputs are H.264, HEVC and VP9 in 8-bit SDR. H.264 output, real 1080p-to-720p browser playback, audio passthrough and seeking have been tested. HDR tone mapping, 10-bit processing, subtitle burn-in, rotated video and other codecs are not certified by these tests. The wrapper keeps the existing FFmpeg path for unsupported requests or unavailable hardware services; it logs which path was selected.

The clean image includes compiled ARM64 tools. Source installation requires the matching hardware bundle under `/usr/share/redmi-nas-hardware` (or `REDMI_NAS_HARDWARE_BUNDLE`). `hardware/runtime-lock.json` records the distributed file hashes. This prevents silently mixing tools or kernel modules from another build.

Build `surface-transcode.cpp` with Android NDK r27b, API 29 or later, using `-std=c++17 -O2 -lmediandk -landroid -lEGL -lGLESv2`. Build `ffmpeg-bridge.go` with Go for `GOOS=linux GOARCH=arm64 CGO_ENABLED=0`, using `-trimpath`. Python 3 and the existing LXC runtime run the broker. The runtime bundle is part of the private clean-image candidate until binary release validation is complete.
