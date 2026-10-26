# Third-party notices

This repository contains a source/configuration adaptation, not a replacement ownership claim over its dependencies.

| Included material | Origin | License |
| --- | --- | --- |
| Linux kernel configuration and module source patches | MiCode public ruby / MTK kernel module trees, themselves based on Linux and MediaTek sources | GPL-2.0-only, subject to individual upstream file notices |
| Homeio hardware reporting changes and reviewed installer functions | doctor-io/homeio v1.10.3 | AGPL-3.0-only |
| Display wake, MediaTek DMA-BUF adapter and integration scripts | José Miranda (Xcat2008), this project | AGPL-3.0-only |

Dependencies obtained separately (Droidian/Debian packages, Halium, libhybris, Android vendor libraries, Docker, PostgreSQL, nginx, Jellyfin and LinuxServer.io images) retain their own licenses. No factory image or proprietary firmware is included. Follow the relevant upstream license and corresponding-source requirements when redistributing binaries or a modified system. A complete redistributable system image has not been prepared by this release.

The upstream Homeio license is included unchanged in `LICENSES/AGPL-3.0-only.txt`. Linux's GPLv2 license text is included in `LICENSES/GPL-2.0-only.txt`. The repository does not relicense GPLv2 kernel material under AGPL.
