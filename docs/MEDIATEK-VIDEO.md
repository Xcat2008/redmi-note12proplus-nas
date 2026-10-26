# Hardware video on the Redmi NAS

The current bridge uses **MediaTek hardware decoding → Mali GPU resizing → MediaTek H.264 hardware encoding**. FFmpeg copies the resulting video into Jellyfin's HLS output and handles audio. Video acceleration here does not automatically accelerate every other application.

![Video path](assets/mediatek-video.svg)

## Implementation

The [native bridge](../apps/jellyfin/mediatek/full/README.md) uses named MediaTek Codec2 components through the Android services already supplied by Droidian. Decoded hardware buffers are imported directly into EGL. An OpenGL ES shader resizes them; native fences prevent reuse before GPU work completes. The H.264 encoder receives a surface rather than CPU-converted raw video.

A small transport writer preserves the hardware codec's presentation timestamps, including after a seek. The local broker accepts an already-open media descriptor. It has no network listener and does not grant the Jellyfin container Android binder access, the host PID namespace or privileged mode. The container's existing read-only adapter mount also exposes the local socket.

Android's 32-bit vendor services require thread identifiers below 65536. A persistent `kernel.pid_max=65535` avoids their startup failures after long periods of process churn. The video service also selects the Codec2 configuration and waits for the media resource manager before accepting work.

The earlier [ION/DMA-BUF adapter](../apps/jellyfin/mediatek/mediatek-dmabuf-bridge.c) remains available for FFmpeg's `h264_v4l2m2m` encoder. Unsupported requests or unavailable native services retain this existing path, with the reason logged. A process-local preload is used only by that fallback, not system-wide.

## Persistence

The clean candidate contains the compiled ARM64 tools, source, matching hardware bundle and systemd units. [Hardware installation](../scripts/install-hardware-services.sh) verifies bundle hashes, installs the modules and enables the services. The NAS installer applies it after the original video adapter. Homeio's existing Jellyfin materialization hook restores the wrapper and mounts after a catalog reinstall.

Each installation creates its own accounts and keys. No personal Jellyfin database, API key, library, Wi-Fi profile, Bluetooth pairing or media file is included. The clean image still needs its complete physical installation and redistribution review before a public binary release.

## Tests on 26 October 2026

| Test | Observed result |
| --- | --- |
| Native full video chain | 180 H.264 frames decoded, resized and encoded; Mali-G68 MC4 / OpenGL ES renderer confirmed |
| Real Jellyfin Web playback | 1920 × 1080 source → 1280 × 720 H.264 HLS at the requested 1.5 Mb/s quality; MP3 audio copied |
| Browser seek | Playback jumped to 185 seconds and continued beyond 191 seconds; requested HLS segments returned HTTP 200 |
| HEVC SDR input | 180 frames decoded by `c2.mtk.hevc.decoder`, resized by Mali and encoded by `c2.mtk.avc.encoder` |
| VP9 SDR input | 180 frames decoded by `c2.mtk.vp9.decoder`, resized by Mali and encoded to H.264 |
| Timestamp and orientation checks | MPEG-TS output carries codec timestamps; coordinate inversion corrected and browser frames inspected |
| Original encoder profile | Earlier empty-config, container-restart and store-reinstall checks passed; encoder-only reference was approximately 60–65 frames/s |

These are tests on one device with selected clips, not a guarantee for every file, resolution or concurrent-client workload. Container CPU alone excludes the native broker and Android codec services; it must not be presented as total transcoding CPU usage.

The main test film was *Big Buck Bunny*, Blender Foundation / www.bigbuckbunny.org, 2008, with the 2013 Sunflower version by Janus Bager Kristensen, licensed [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/). [Original test download](https://download.blender.org/demo/movies/BBB/bbb_sunflower_1080p_30fps_normal.mp4.zip). It is not included in the image.

## Scope

Validated native inputs are H.264, HEVC and VP9 in 8-bit SDR, with H.264 output. HDR tone mapping, 10-bit processing, subtitle burn-in, interlaced/anamorphic/rotated media and other formats are not certified by these tests. The wrapper preserves the existing FFmpeg path for unsupported processing. Audio conversion, HLS packaging and application services still use CPU.

Direct play remains preferable when the client accepts the original file. Do not select NVIDIA or another unrelated backend for this phone. After changing the kernel, Android hardware stack or pinned Jellyfin/FFmpeg version, repeat the real-playback, seek, fresh-configuration and reinstall checks.
