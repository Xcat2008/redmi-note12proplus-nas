![Redmi NAS — José Miranda](docs/assets/redmi-nas-hero.png)

*Project cover illustration. The screenshots below show the real running device.*

# Redmi Note 12 Pro+ NAS

🇵🇹 **Made in Portugal — a project by Portuguese developer José Miranda (Xcat2008).**

**A retired phone, a native Linux system, and a home server you can manage from a browser.**

Project by **José Miranda (Xcat2008)** · GitHub: [Xcat2008](https://github.com/Xcat2008)

[Quick start](docs/QUICKSTART.md) · [Português](README.pt-PT.md) · [Porting guide](docs/INSTALLATION.md) · [Tested hardware](docs/COMPATIBILITY.md) · [Credits](CREDITS.md)

![System architecture](docs/assets/architecture.svg)

This project documents a working NAS experiment on a **Xiaomi Redmi Note 12 Pro+ 5G (22101316UG / rubypro)** with a MediaTek Dimensity 1080, 8 GiB of physical RAM and 256 GB of internal storage. Android userspace was replaced with **Droidian / Debian**, using the device's vendor kernel and Halium compatibility stack. **Homeio** provides the web desktop and application management; Docker runs applications on ARM64.

The phone keeps a normal Phosh desktop. Homeio runs in the background and starts automatically; the display can switch off while the NAS remains available over Wi-Fi.

## Running on the actual phone

These are live Homeio captures from the project device, taken on 26 October 2026. The web desktop is served by native Linux on the Redmi, over Wi-Fi.

![Homeio running on the Redmi NAS](docs/screenshots/homeio-live-desktop.png)

| Eight CPU cores | Integrated GPU |
| --- | --- |
| ![Six Cortex-A55 and two Cortex-A78 cores](docs/screenshots/homeio-cpu.png) | ![ARM Mali-G68 MC4](docs/screenshots/homeio-gpu.png) |

<details>
<summary>Memory details and capture notes</summary>

![Memory reported by Linux](docs/screenshots/homeio-memory.png)

The phone has 8 GiB of physical RAM. Linux reports about 7.4 GiB after platform reservations. Live readings fluctuate. MediaTek video decoding and H.264 encoding, together with Mali GPU resizing, have now been exercised in the Jellyfin browser player. Network identifiers are hidden, and the Jellyfin shortcut is omitted for the capture. See [capture notes](docs/SCREENSHOTS.md).

</details>

## Latest development baseline

The source update adds native Mali Vulkan presentation, CPU-tier placement, bounded duplicate-frame pacing and kernel/runtime stability fixes. [Technical measurements and integration limits](docs/PERFORMANCE.md) cover the current timing and thermal constraints. A refreshed clean image containing this baseline has not been released.

The consolidated [native gaming profile](docs/NATIVE-GAMING.md) adds independent Steam launch, update/recovery handling and clean-image setup. Another unattended full NAS reboot passed on 28 October 2026. The candidate remains a developer validation build.

## Proxmox and hardware virtual machines

The configured Redmi now runs **Proxmox VE 9.2.20 ARM64 with hardware KVM**. A full Debian 13 guest with eight vCPUs passed calculation on all eight physical cores, disk persistence, private networking, web-console and restart checks. The old kernel's mixed-cluster cache mismatch is handled by the scoped QEMU compatibility adapter.

The [Proxmox guide](docs/PROXMOX.md) and [compatibility source](apps/proxmox/README.md) are public. This remains an **experimental optional profile**: the existing clean image candidate does not contain it, and a fresh unattended installation is not released. The NAS reboot result above predates this KVM profile; its full phone reboot is still pending validation.

## Release status

**Developer preview. The NAS runs on the project device. A clean boot/data image and a guarded Windows installer have also been built, but still need a complete physical installation test before a public binary release.**

The original device has been tested, but the public procedure has not yet been repeated on a second clean phone. The candidate uses individual setup credentials rather than a copy of the author’s configured system. Read the [installer status](docs/IMAGE-INSTALLER.md) and [installation guide](docs/INSTALLATION.md) before deciding to replicate it.

| Capability | Result on the project device |
| --- | --- |
| Native Linux boot and systemd | Working |
| Wi-Fi and automatic reconnect | Working |
| Homeio browser desktop | Working |
| Automatic NAS startup after reboot | Verified on the NAS baseline; full phone reboot of the experimental KVM profile pending |
| NAS stays available with display off | Working after the mobile-power-saver fix |
| Docker ARM64 container | Working |
| Jellyfin | Real 1080p → 720p browser playback with hardware decode, Mali resize and hardware H.264 encode; seeking verified |
| Physical power and volume buttons | Working with the documented adaptations |
| CPU / GPU / RAM reporting | ARM hardware reporting patch included |
| CPU energy profiles | Homeio controls Power saver / Balanced / Performance; corrected native policy, factory limits and automatic GPU/memory DVFS |
| Steam Big Picture | Official native ARM64 client, separate Homeio/Moonlight entry and Mali composition; Steam games are not certified |
| RetroArch PS2 adaptation | Native Mali backend and accepted presentation adapter; performance depends on software and temperature |
| USB hub, simultaneous charging and external disks | Not yet tested |
| Bluetooth | Homeio radio/discovery controls verified; Xbox pairing and in-game input confirmed on the project device |
| Proxmox / KVM ARM64 | Eight-vCPU Debian guest tested on all physical cores; experimental source profile, not in the current image candidate |
| SIM / mobile data and cameras | Not validated |
| Jellyfin video acceleration | H.264 / HEVC / VP9 SDR decoding, Mali resize and H.264 encoding verified |

## H.264 encoding on MediaTek

![MediaTek video path](docs/assets/mediatek-video.svg)

The full video bridge uses the **MediaTek video engines** for decode and H.264 encode, with **Mali OpenGL ES** resizing between them. FFmpeg handles audio and HLS packaging. Real 1080p → 720p browser playback and a seek to 185 seconds passed; HEVC and VP9 inputs were also exercised. Performance depends on the media and concurrent load. The earlier ION/DMA-BUF encoder adapter remains as a fallback. See [video validation](docs/MEDIATEK-VIDEO.md).

The fix is included in the clean image candidate and in the automatic NAS installer. Homeio applies the devices, permissions, FFmpeg path and first-run encoding profile when Jellyfin is installed from the store. [Technical details and validation](docs/MEDIATEK-VIDEO.md).

## What is included

- The kernel configuration used for the native Linux NAS.
- Source revisions and compatibility patches for the connectivity modules.
- The display wake bridge and NAS power-policy setup.
- Homeio ARM hardware-reporting changes, with fixture tests.
- [CPU energy profiles and hardware-scaling validation](docs/ENERGY.md).
- [Bluetooth controls in Homeio Settings](docs/BLUETOOTH.md), without using the phone's screen.
- The MediaTek DMA-BUF adapter, automatically configured for fresh Jellyfin store installs.
- The Jellyfin compatibility fix and a portable software-mode compose example.
- [Experimental Proxmox/KVM compatibility source and validation](docs/PROXMOX.md).
- Installation, recovery, validation and licensing notes.

The custom 3D enclosure is a separate personal build and is not included here. Firmware blobs, factory images, personal data, device credentials and configured root filesystems are not distributed.

## Start here

1. Read the [quick start](docs/QUICKSTART.md), then check the exact model and [compatibility matrix](docs/COMPATIBILITY.md).
2. Read the [installation and recovery notes](docs/INSTALLATION.md).
3. Use the [pinned source manifest](sources.lock.json) and build notes; do not flash an image intended for a different Redmi model.
4. On an already working native Droidian installation, use the scripts in `scripts/` after reviewing them.
5. Follow [validation](docs/VALIDATION.md), including a display-off test, before relying on it as a NAS.

This is an independent community experiment, not an official Xiaomi, Droidian or Homeio device release. 

## Support the project

The author’s GitHub Sponsors application is awaiting approval. A support link will be added when the profile is live. Contributions will support José Miranda’s work on this project; please also consider supporting the upstream projects listed in [credits](CREDITS.md).

Contributions, reproducible bug reports and documentation improvements are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md) before posting logs.

## License

Original project scripts and documentation are licensed under **AGPL-3.0-only**, except where an individual file states otherwise. Kernel configuration and kernel/module patches retain **GPL-2.0-only** compatibility and upstream notices. Homeio-derived code remains **AGPL-3.0-only**. See [LICENSE.md](LICENSE.md) and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
