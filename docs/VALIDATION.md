# Validation checklist

The working device passed these checks on 26 October 2026. These historical checks are supplemented by the supervised rc2 clean-install results below; independent testing on a second device remains pending.

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

The permanent Homeio materialization hook then passed six regression tests, ESLint, a full Next production build and the server TypeScript build. Two uninstall/install cycles using the untouched catalog source passed, preserving application data (`removeVolumes=false`); Jellyfin became Healthy after both. A subsequent MediaTek profile passed nine compose regression tests, ESLint, both production builds, a fresh empty-config container and another store uninstall/install cycle with the application data preserved. Actual browser playback then used the native `h264_v4l2m2m` encoder on `/dev/video2` through ION/DMA-BUF. That initial encoder-only sample ran around 60â€“65 frames/s. The subsequent native media bridge passed full hardware decoding, Mali resizing and H.264 encoding, including browser playback and seeking. HEVC and VP9 SDR samples each produced 180 decoded, resized and encoded frames. See [video validation](MEDIATEK-VIDEO.md). External-disk libraries remain untested. The Homeio app-store catalog is not universally certified for the phone: each app's CPU architecture, devices, permissions and power requirements need checking.

## Homeio Bluetooth controls

The native BlueZ panel passed six service tests. Browser checks verified radio power on/off, discovery, stopping a search, automatic stop after 45 seconds and discovery continuing while switching Settings sections. Unauthenticated requests, cross-origin mutations and malformed device addresses were rejected. The Next.js production build and server TypeScript build passed. Physical Xbox pairing and button input were subsequently confirmed on the project device.

## Energy and hardware scaling

The native power manager now applies and persists the three CPU profiles, uses schedutil as its NAS balanced baseline and prevents screen-off dozing from overriding that policy. Native tests covered both clusters and profile persistence across power-daemon reactivation. Homeio's three controls, authentication, origin checks and rejection of invalid profile identifiers passed browser tests. GPU frequency scaled from 385 to 950 MHz during an offscreen Mali GLES workload; a 512 MiB full-buffer copy/integrity probe reached the highest DDR operating point without a mismatch. Details and limits are in [ENERGY.md](ENERGY.md).

## Not yet established

- Hub host-mode operation with simultaneous PD charging.
- External Ethernet and three external disks, including drive spin-up power.
- SMB throughput and sustained real file-transfer checks.
- SIM/mobile data and camera functionality.
- A public image reproducibly installed on a second clean device.

## 27 October stability and gaming update

The later native Vulkan/PS2 work, ordinary reboot fixes, thermal observations and remaining microstutters are recorded in [PERFORMANCE.md](PERFORMANCE.md). Physical Xbox pairing and input have now been confirmed on the development device; independent clean-install validation remains pending.

## Experimental Proxmox/KVM profile

The [Proxmox guide](PROXMOX.md) records the separate 29 October 2026 validation: eight-vCPU Debian ARM64, work on all eight physical CPUs, disk persistence, DHCP/DNS/HTTPS, guest agent, serial web console, guest/environment restarts and package-maintenance hooks. The two eight-second calculation runs are functional regression checks, not endurance certification. The earlier NAS reboot result does not certify the new KVM kernel/platform. The later rc2 clean installation, optional PVE activation and full phone reboot passed on this already EL2-enabled phone. Stock-device EL2 activation, nested LXC, Windows ARM and GPU passthrough remain pending. See the [sanitized test scope](../apps/proxmox/validation.json).

## Corrected rc2 clean installation — 29 October

The project phone was erased and reinstalled using the corrected public flash and USB-personalization functions. The host test wrapper resumed personalization after a missing Python dependency; the phone's NAS installation itself completed automatically without repairs. Homeio reached first registration, data storage expanded, RetroArch used the Mali GPU and launching Steam stopped RetroArch. Memory extension, battery care, personal automatic backups and Proxmox start disabled in the image.

Optional Proxmox activation then passed. A 512 MiB, eight-vCPU ARM64 smoke guest positively confirmed hardware KVM, tested memory and its isolated network, and powered off. Full phone restart restored the NAS both before and after enabling Proxmox, without buttons or cable intervention. The VM and credentials created for this validation are not in the distribution image.

This validates the supervised CLI/function path on one phone with EL2 already enabled. It does not certify a full graphical-assistant click-through, stock-device EL2 activation, long-duration stability or binary redistribution. See [the sanitized machine-readable record](../image/validation-rc2.json).
