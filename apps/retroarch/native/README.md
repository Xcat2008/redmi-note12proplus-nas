# Native Vulkan adapters

These source components were exercised on the project Redmi Note 12 Pro+ 5G with RetroArch 1.20, ARMSX2 and a native Linux build of MaliSX2. They preserve the upstream emulator binary and scope the Vulkan compatibility layer to the gaming process.

The public NAS installer still uses the earlier GLES session. These adapters are an advanced development path, not an automatic upgrade or a new ready-to-flash image. Integrating them into a clean installation remains pending.

## Components

- `libretro-adapter.c`: native renderer selection, isolated settings and numerical timing counters. In the Vulkan session, duplicate callbacks are coalesced while polling yields for 1 ms; the wait budget is 20 ms. `ARMSX2_WAIT_FOR_FRAME=0` disables this pacing path.
- `cpu-tier-placement.h`: the EE thread can use the highest-capacity CPU tier when at least two such cores exist. Other emulator threads keep their own masks. The saved mask is restored on unload/deinitialization, narrower explicit masks are respected, and `ARMSX2_EE_PERFORMANCE_TIER=0` opts out. No frequency, voltage or thermal limits are changed.
- `vulkan-x11-bridge.c`: X11 presentation for the native Mali driver, pipelined readback and XShm. Readback prefers host-cached memory, falls back to coherent memory, and invalidates the mapping **after the producing GPU fence** before CPU access. DMA synchronization is retained.

## Build and test

On a Linux development machine, install a C compiler, curl, Vulkan headers, X11/Xext/XCB headers and their development libraries. Debian package names include `build-essential curl libvulkan-dev libx11-dev libxext-dev libxcb1-dev`.

```sh
sh apps/retroarch/native/build.sh
sh apps/retroarch/native/tests/run.sh
```

The scripts fetch the versioned Libretro API header and verify its SHA-256. The adapter tests use synthetic callbacks and an isolated thread; no games or BIOS files are read. The CPU-tier test skips on hosts without heterogeneous CPU capacity data. Building the libraries does not install them or change a running session.

On the tested ARM64 device, the process uses `LD_LIBRARY_PATH=/usr/local/lib/redmi-nas/retroarch/vulkan`, `NAS_VK_NATIVE_DRIVER` pointing to the separately built native `libvulkan_malisx2.so`, and `ARMSX2_RENDERER=Vulkan`. The upstream ARMSX2 library is expected at `/usr/local/lib/redmi-nas/retroarch/armsx2-official.so`. The X11 display and IPC namespace must match the display container. This is not a drop-in global Vulkan replacement; do not replace distribution graphics libraries with this bridge.

The native MaliSX2/Mesa build and upstream emulator binary are obtained separately. Versions are recorded in `sources.lock.json`; their redistribution review is separate from these source adapters. Rebuild dependencies with local build paths remapped before distributing binaries.

Read [performance and stability notes](../../../docs/PERFORMANCE.md) for measurements and remaining limits. These source files use GPL-3.0-or-later; upstream dependencies keep their own notices.
