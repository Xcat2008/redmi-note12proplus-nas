# Validation checklist

The working device passed these checks on 26 October 2026. Public wrapper scripts still require an independent clean-install test.

1. `uname -r`: `4.19.191-g914ba8403bb3`; PID 1 is systemd.
2. All eight CPUs online; two cpufreq policies use schedutil, with cluster maxima 2.0 / 2.6 GHz.
3. GPU sysfs identifies Mali-G68, and the compositor logs show actual GLES rendering.
4. Homeio, nginx, PostgreSQL, Docker, upload and DBus helpers are active after reboot.
5. A native ARM64 Docker container runs successfully.
6. Wi-Fi reconnects automatically; access works over LAN independently of the USB cable.
7. Wait at least 65 seconds with the display off. Repeat HTTP requests to Homeio; NAS service cgroups must remain unfrozen (`cgroup.freeze=0`).
8. Physical power off/wake and volume buttons work. Display timeout is 15 seconds; full-system suspend is disabled for NAS service availability.
9. Restart the phone and repeat LAN, service and display-off checks. On the original device the NAS services started before the mobile UI finished loading.
10. Check RAM with `free -h`; use MemAvailable for available memory. Kernel-reserved memory and filesystem cache are not a memory leak.

## Jellyfin result

The catalog download succeeded, but its compose template tried to mount `/dev/vcsm`, `/dev/vchiq`, Raspberry Pi video nodes and `/opt/vc/lib`. Docker rejected the missing hardware. Removing these optional device mappings and the Broadcom library mount allowed the ARM64 container to start. Homeio's installation operation completed and the Jellyfin web page returned HTTP 200; `/health` returned `Healthy` from another computer on the LAN.

The permanent Homeio materialization hook then passed six regression tests, ESLint, a full Next production build and the server TypeScript build. Two uninstall/install cycles using the untouched catalog source passed, preserving application data (`removeVolumes=false`); Jellyfin became Healthy after both. Media playback has since been tested as described below. External-disk libraries remain untested. The Homeio app-store catalog is not universally certified for the phone: each app's CPU architecture, devices, permissions and power requirements need checking.

## Browser playback and transcoding test

On **26 October 2026**, the project device ran **Jellyfin 12.2.0**, the LinuxServer ARM64 image `12.2ubu2604-ls53`, and **jellyfin-ffmpeg 8.1.3**. The test library used the complete **Big Buck Bunny, Sunflower 1080p/30** video from the [Blender download server](https://download.blender.org/demo/movies/BBB/): H.264 video, MP3/AC-3 audio, 634.6 seconds, 276,134,947 bytes. Film credits were retained. The browser was an isolated Chrome client on the LAN.

| Test | Observed result |
| --- | --- |
| Automatic quality / 1080p direct play | Actual video displayed in the browser; HTTP 206 MP4 delivery, with no server video encoder |
| Forced 1.5 Mbps quality | Real HLS playback at 1280 × 720; video transcoded with `libx264`, preset `veryfast`; MP3 audio copied |
| Client frames during forced transcode | 837 presented frames, 0 dropped in the recorded sample; playback position advanced to about 40 seconds |
| Server transcoding rate | Roughly 90–97 fps in the sampled interval, about 3× the 30 fps source |
| Server acceleration reported by Jellyfin | `HardwareAccelerationType: none`, `IsVideoDirect: false` |
| Load during buffering | A container sample reached about 706% CPU, approximately seven CPU cores; this was not an idle or long-term average |

This was a short playback/transcoding test, not a full-film endurance test, a 4K test or a concurrent-stream capacity claim.

### MediaTek video hardware

The kernel exposes `/dev/video1` (`mtk-vcodec-dec`) and `/dev/video2` (`mtk-vcodec-enc`), along with VCU/ION devices. Standard V4L2 capability and format enumeration succeeded. Those nodes are separate from the Mali graphics device used by the desktop.

Bounded, temporary FFmpeg containers were given the relevant device nodes. H.264 encoding was tested with YUV420P and NV12 input. The driver was selected, but capture dequeue returned an input/output error and the output contained **zero encoded packets**. A nominal FFmpeg exit code of zero was therefore not counted as success. A further host-PID/unlimited-memlock compatibility probe had the same empty-output result. H.264 hardware decoding also failed to return frames and reported buffer-allocation errors.

These tests establish that hardware video acceleration is **not working through the current FFmpeg/driver stack**. They do not prove that the MediaTek video block is incapable of acceleration under another supported integration. The [Jellyfin acceleration documentation](https://jellyfin.org/docs/general/post-install/transcoding/hardware-acceleration/) does not list this MediaTek stack as a validated method. Mali/OpenGL desktop rendering is not evidence of a usable video transcoding pipeline.

The working Jellyfin configuration remains in software mode. The temporary test account, API key and probe containers were removed; the test library and video were retained. Post-test `/health` returned `Healthy`.

## Not yet established

- Hub host-mode operation with simultaneous PD charging.
- External Ethernet and three external disks, including drive spin-up power.
- SMB throughput and sustained real file-transfer checks.
- Bluetooth, SIM/mobile data and camera functionality.
- A public image reproducibly installed on a second clean device.
