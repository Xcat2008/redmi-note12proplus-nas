# Licensing

Copyright (C) 2026 José Miranda and contributors, for original project material.

Original scripts and documentation: **GNU Affero General Public License v3.0 only (AGPL-3.0-only)**, in `LICENSES/AGPL-3.0-only.txt`.

Exceptions and upstream components:

- `kernel/` configurations and patches to Linux/MediaTek kernel modules: **GPL-2.0-only**, with original upstream notices retained. See `LICENSES/GPL-2.0-only.txt` and the exact source repositories.
- Homeio-derived code and installer functions: **AGPL-3.0-only**, copyright their upstream authors plus the local modifications. Homeio itself is not authored by this project.
- Native Libretro ABI/CPU and Vulkan presentation adapters with individual notices: **GPL-3.0-or-later**. Their file headers govern; the AGPL default does not replace those notices.
- The adapted Mobile Power Saver daemon retains its upstream **GPL-3.0** terms in `hardware/power/`. The Bluetooth/bluebinder adaptation retains **GPL-2.0-or-later**, including `hardware/bluetooth/COPYING` and per-file notices.
- The Proxmox cache ioctl adapter, QEMU launcher and firmware helper use the **MIT** notices in their files and `apps/proxmox/LICENSE.MIT`; the surrounding original integration scripts retain AGPL-3.0-only.
- Bundled third-party emulation cores, fonts, runtimes and packages retain their upstream licences. **Genesis Plus GX is not covered by the project's AGPL licence and restricts commercial use/distribution**; see `LICENSES/Genesis-Plus-GX-LICENSE.txt`. A project support link does not waive that restriction.
- Firmware, proprietary Android vendor libraries, factory ROMs and the configured device filesystem are not licensed or distributed by this repository.

Software is supplied without warranty under the applicable license. This repository's license does not grant rights to third-party trademarks or change upstream licenses. See `THIRD_PARTY_NOTICES.md` and `CREDITS.md`.
