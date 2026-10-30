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

The experimental Proxmox integration adds original maintenance/reporting wrappers under AGPL-3.0-only, with the cache ioctl adapter, QEMU launcher and firmware helper under the MIT notices in their files and `apps/proxmox/LICENSE.MIT`. Original PVE vendor modules are obtained separately and retain their package licenses. The repository source bundle contains no Proxmox/QEMU executable, LXCFS library, EDK2 firmware image or configured VM. The separate rc3 binary release includes a clean optional ARM64 userspace and preserves its upstream package notices and corresponding sources. LXCFS uses LGPL-2.1-or-later; EDK2's general license is BSD-2-Clause-Patent with per-file exceptions. A later binary image must include the corresponding upstream notices and source obligations for its actual packages.

Dependencies obtained separately (Droidian/Debian packages, Halium, libhybris, Android vendor libraries, Docker, PostgreSQL, nginx, Jellyfin, RetroArch, its cores, Sunshine, Selkies and LinuxServer.io images) retain their own licenses. No factory image or proprietary firmware is included. Follow the relevant upstream license and corresponding-source requirements when redistributing binaries or a modified system. The separate experimental rc3 binary package is accompanied by its installed-source inventory, corresponding-source parts and original package/license notices.

The upstream Homeio license is included unchanged in `LICENSES/AGPL-3.0-only.txt`. Linux's GPLv2 license text is included in `LICENSES/GPL-2.0-only.txt`. The repository does not relicense GPLv2 kernel material under AGPL.

The clean validation candidate includes a Genesis Plus GX core from libretro/Genesis-Plus-GX, commit `60bee4c724859710ce05672239e5b601ad01382e`. Its upstream license restricts commercial redistribution and contains separate notices for bundled components; it must not be described as GPL-only. The complete upstream notice is preserved in [LICENSES/Genesis-Plus-GX-LICENSE.txt](LICENSES/Genesis-Plus-GX-LICENSE.txt). No console game, BIOS or author media accompanies this core. The experimental rc3 release preserves this license and corresponding source. These components must not be sold or relicensed contrary to their original terms.
