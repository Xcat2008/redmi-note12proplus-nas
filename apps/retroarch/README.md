# RetroArch and Sunshine in Homeio

The NAS setup installs the gaming stack in Homeio. Open **RetroArch** from the Homeio desktop to use the Ozone interface in a browser. The phone's screen and application menu are not required. The stack includes Sunshine for Moonlight clients on TVs and other devices. Use Homeio's existing context menu to start, stop or uninstall it; the NAS and Jellyfin run independently.

The native renderer was tested with **Mali-G68 MC4 / OpenGL ES 3.2** in the application's virtual X11 display, with audio routed to that session. It shares the display container's network and IPC namespaces while retaining the phone's native graphics libraries. A scoped BGRA adapter fixes the X11 buffer byte order without replacing the phone's Wayland graphics libraries. A solid-red GPU output was verified against the X11 pixel value.

The later development baseline adds [native Vulkan source adapters and PS2 tuning](native/README.md). PS2 play on the TV improved substantially on the project phone, with occasional short pauses remaining. This opt-in native path is not yet integrated into a freshly validated public image. See [performance notes](../../docs/PERFORMANCE.md).

Browser capture and Sunshine currently encode video in software. Jellyfin's MediaTek hardware-video integration does not automatically provide an encoder to Sunshine. The browser defaults to 1280×720 at 30 FPS. PS2/PS3 gameplay is not certified by installing this stack.

The image includes the Debian-packaged Nestopia (NES) and Gambatte (Game Boy) cores. Additional cores can be installed through RetroArch's updater into the user's writable core directory. The installed PCSX-ReARMed and experimental ARMSX2 ARM64 libraries loaded in the development system, but this older packaged path is not the later tested native Vulkan baseline and does not certify PS2 compatibility.

| Location | Purpose |
| --- | --- |
| `/DATA/Games/ROMs` | User-supplied games |
| `/DATA/Games/BIOS` | User-supplied firmware required by a core |
| `/DATA/Games/Saves` | In-game saves |
| `/DATA/Games/States` | Save states |
| `/DATA/Games/Screenshots` | Screenshots |
| `/DATA/AppData/custom-retroarch/native/retroarch.cfg` | NAS application settings |
| `~/.local/share/retroarch/cores` | Writable cores directory |

Upload games through Homeio's file manager. In RetroArch, choose **Load Content → Start Directory** to browse the ROM folder. No commercial games, console BIOS files or personal save data are included in the project image.

The clean image's network-connected first setup downloads the pinned container base and Sunshine package and builds the local image. The source integration is included in the installer; an older image candidate does not acquire it until rebuilt.

The browser UI uses the existing Homeio session on HTTPS port **3443**. Sunshine's configuration UI is on HTTPS port **3444**, also behind the Homeio session check. Complete Sunshine's own initial administrator setup there and enter the pairing PIN shown by Moonlight. Add the NAS's LAN address in Moonlight. UPnP is disabled. TV/controller streaming and a PS2 workload have since been exercised on the project device with the native development path. Installing the earlier stack alone does not reproduce or certify those results.

Upstream: [RetroArch / Libretro](https://www.retroarch.com/), [Debian](https://packages.debian.org/trixie/retroarch), [LinuxServer.io](https://github.com/linuxserver/docker-retroarch), [Sunshine](https://github.com/LizardByte/Sunshine), [Moonlight](https://moonlight-stream.org/) and [Droidian libhybris](https://github.com/droidian/libhybris). These projects and each emulator core retain their own authors and licenses; installed package notices remain available in `/usr/share/doc` and the packaged assets.
