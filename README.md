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

The phone has 8 GiB of physical RAM. Linux reports about 7.4 GiB after platform reservations. Live readings fluctuate. GPU identification is confirmed; MediaTek hardware transcoding failed with the current stack; CPU transcoding has been tested. See [validation](docs/VALIDATION.md). Network identifiers are hidden, and the Jellyfin shortcut is omitted for the capture. See [capture notes](docs/SCREENSHOTS.md).

</details>

## Release status

**Developer preview. The NAS runs on the project device. A clean boot/data image and a guarded Windows installer have also been built, but still need a complete physical installation test before a public binary release.**

The original device has been tested, but the public procedure has not yet been repeated on a second clean phone. The candidate uses individual setup credentials rather than a copy of the author’s configured system. Read the [installer status](docs/IMAGE-INSTALLER.md) and [installation guide](docs/INSTALLATION.md) before deciding to replicate it.

| Capability | Result on the project device |
| --- | --- |
| Native Linux boot and systemd | Working |
| Wi-Fi and automatic reconnect | Working |
| Homeio browser desktop | Working |
| Automatic NAS startup after reboot | Working |
| NAS stays available with display off | Working after the mobile-power-saver fix |
| Docker ARM64 container | Working |
| Jellyfin | Direct playback at 1080p and CPU video transcoding to 720p tested; persistent Raspberry Pi device-mapping compatibility included |
| Physical power and volume buttons | Working with the documented adaptations |
| CPU / GPU / RAM reporting | ARM hardware reporting patch included |
| USB hub, simultaneous charging and external disks | Not yet tested |
| Bluetooth, SIM / mobile data and cameras | Not validated; Bluetooth currently reports a missing rfkill device |
| Jellyfin hardware transcoding | MediaTek V4L2 tests failed with the current stack; CPU mode retained |

## What is included

- The kernel configuration used for the native Linux NAS.
- Source revisions and compatibility patches for the connectivity modules.
- The display wake bridge and NAS power-policy setup.
- Homeio ARM hardware-reporting changes, with fixture tests.
- The Jellyfin compatibility fix and a portable compose example.
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
