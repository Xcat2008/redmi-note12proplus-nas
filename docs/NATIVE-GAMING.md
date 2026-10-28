# Native gaming profile

The current integration uses separate **RetroArch** and **Steam** entries in
Homeio and Sunshine. Applications start on demand. The shared display, audio
and streaming infrastructure remains available when either application stops.
Steam does not run inside RetroArch and does not require an emulator process.
An active game must be closed before switching applications.

Steam Big Picture uses Valve's native ARM64 client with Mali/ANGLE Vulkan
composition. Vector rasterization stays on the CPU to avoid the icon corruption
observed with forced GPU rasterization. The dedicated presentation bridge handles
event-driven frames and window resizing; it does not replace system Vulkan or
the accepted RetroArch bridge. Running the interface does not establish that
every Steam game, x86 translation layer or anti-cheat system works on this phone.

The first network-connected NAS setup downloads the pinned official client
directly from Valve and verifies every package size and SHA-256. No author's
Steam account or proprietary client archive is included in this source tree or
the clean image. Each user signs in personally. A local, manual program recovery
cache is created during setup; it excludes personal NAS data and account state.
Steam's explicit update-restart exit code is handled by systemd. Ordinary Stop
leaves the application stopped.

RetroArch uses Ozone and the native Mali backend. The candidate includes the
Genesis Plus GX core and the ARMSX2 compatibility adapter, with upstream generic
defaults. There are no per-game speed hacks, BIOS files, ROMs, saves, playlists,
game screenshots or personal library names. PS2 performance depends on the game,
accuracy settings and temperature; factory thermal protections remain enabled.
The Xbox profiles and View + Menu shortcut are included. For Moonlight on a TV,
the controller may instead be paired to the TV and forwarded by Moonlight.

Upload files through Homeio:

| Content supplied by the user | Directory |
| --- | --- |
| Games | `/DATA/Games/ROMs`, organised by system |
| PS2 BIOS | `/DATA/Games/BIOS/PS2` |
| Other system BIOS | `/DATA/Games/BIOS` |
| Media | `/DATA/Media/Filmes` or `/DATA/Media/Series` |

The browser stream defaults to 720p30. Browser/Sunshine encoding uses software;
Mali graphics composition and Jellyfin's hardware video pipeline are distinct.
No gaming FPS or latency guarantee is inferred from a Jellyfin playback test.

## Persistence and validation

The project phone completed another unattended normal reboot on 28 October 2026;
NAS service recovery took 89.9 seconds. Homeio, Jellyfin, Sunshine, Bluetooth,
CPU policy, the USB console workaround and scoped GPU logging policy were
checked afterwards. Steam then started independently with its Mali bridge and
no RetroArch process. A synthetic Jellyfin hardware decode → Mali resize → H.264
encode test produced all 60 requested frames after reboot.

The source overlay applies to a fresh Homeio v1.10.3 checkout. Its Bluetooth,
hardware, energy and browser-launch tests and the complete production build
passed. The distribution Mali backend was rebuilt with neutral source paths and
created a device successfully on the actual Mali-G68. The accepted emulator
bridge remains byte-for-byte unchanged in the candidate runtime.

The clean image is a **developer validation candidate**. Offline filesystem,
architecture, dependency, source and privacy checks do not replace a full clean
physical installation test. Normal flashing remains guarded while that test is
unperformed. No live user installation is erased to carry out an offline audit.

Memory extension and battery care are optional and off in a clean installation.
Automatic personal backups are also off. Existing users' choices are preserved
by the running installation; the image contains no copy of the owner's settings.

Project adaptation: José Miranda (Xcat2008), Portugal. See [credits](../CREDITS.md)
and the individual upstream licenses.
