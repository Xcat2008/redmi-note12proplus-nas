# Third-party notices

This repository contains a source/configuration adaptation, not a replacement ownership claim over its dependencies.

| Included material | Origin | License |
| --- | --- | --- |
| Linux kernel configuration and module source patches | MiCode public ruby / MTK kernel module trees, themselves based on Linux and MediaTek sources | GPL-2.0-only, subject to individual upstream file notices |
| Homeio hardware reporting changes and reviewed installer functions | doctor-io/homeio v1.10.3 | AGPL-3.0-only |
| Mobile Power Saver CPU/profile patch and adapted native daemon | Cédric Bellegarde and Droidian Mobile Power Saver contributors | GPL-3.0 (upstream COPYING); pinned corresponding source and patch in hardware/power/ |
| Display wake, MediaTek DMA-BUF adapter and integration scripts | José Miranda (Xcat2008), this project | AGPL-3.0-only |
| Bluetooth bridge adaptation | mer-hybris/bluebinder and its original Jolla/Intel contributors; local HIDL/VHCI adaptation | GPL-2.0-or-later; see hardware/bluetooth/COPYING and per-file notices |
| Native video bridge, transport writer and broker | José Miranda (Xcat2008), this project | AGPL-3.0-only |
| Homeio gaming integration, native X11 session adapter and scoped BGRA fix | José Miranda (Xcat2008), this project | AGPL-3.0-only |
| Native Libretro ABI/CPU placement and Vulkan presentation adapters | José Miranda (Xcat2008), this project | GPL-3.0-or-later; see LICENSES/GPL-3.0-only.txt |
| Go runtime linked into the FFmpeg bridge executable | The Go Authors | BSD-3-Clause; see LICENSES/Go-BSD-3-Clause.txt |

Dependencies obtained separately (Droidian/Debian packages, Halium, libhybris, Android vendor libraries, Docker, PostgreSQL, nginx, Jellyfin, RetroArch, its cores, Sunshine, Selkies and LinuxServer.io images) retain their own licenses. No factory image or proprietary firmware is included. Follow the relevant upstream license and corresponding-source requirements when redistributing binaries or a modified system. A complete redistributable system image has not been prepared by this release.

The upstream Homeio license is included unchanged in `LICENSES/AGPL-3.0-only.txt`. Linux's GPLv2 license text is included in `LICENSES/GPL-2.0-only.txt`. The repository does not relicense GPLv2 kernel material under AGPL.
