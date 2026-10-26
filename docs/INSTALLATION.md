# Installation and porting notes

## Read this first

This release publishes the working experiment's configuration and adaptations, **not a complete flashable distribution**. The base port still has manual stages; the public procedure has not been verified end to end on a second clean phone. Do not treat a kernel build as a complete ROM. Never flash a 4G model's image onto this 5G model.

The irreversible steps are bootloader unlocking and replacing Android userdata. Back up personal files, app data and authentication codes first. Use firmware for your exact model/region and keep a tested path to FASTBOOT and the complete factory recovery firmware.

## 1. Unlock through Xiaomi

Use the official Xiaomi Community account/bootloader application process where required, then the official **Mi Unlock** desktop tool. Follow the current Xiaomi instructions and any account binding/wait requirements; they can change. Unlocking erases the phone. After the reset, any Xiaomi account activation must be completed by the owner.

The project device was unlocked with Mi Unlock. We did not bypass Xiaomi's account activation or quotas. After Android's initial setup, re-enable USB debugging and authorize the build computer if needed.

## 2. Collect the exact device inputs

- Confirm model **22101316UG**, rubypro / MT6877, and obtain its factory firmware. The test started from **OS2.0.16.0.UMOEUXM**.
- Preserve original boot, vbmeta, vendor-related partitions and a partition inventory before writing anything.
- Obtain the Droidian ARM64 **API 32** rootfs from [the recorded release](https://github.com/droidian-images/droidian/releases/tag/droidian/101.20261023). Use the source manifest for the exact asset/checksum recorded locally.
- Read the [Droidian porting guide](https://github.com/droidian/porting-guide), especially kernel compilation and rootfs creation. Preserve the exact device's Android vendor compatibility stack; this is a Halium port, not a generic mainline ARM installation.

## 3. Build the kernel and connectivity modules

The pinned revisions are in `sources.lock.json`. `kernel/linux-resolved.config` is the NAS configuration actually used; `kernel/linux-nas.config` shows the NAS-specific feature additions. Build with Android clang **r383902 / 11.0.1** and the arm64 / ARM compatibility GNU cross-toolchains.

`scripts/build-kernel.sh BUILD_ROOT` configures and compiles the kernel after you have prepared the sources and toolchain. `scripts/fetch-sources.sh BUILD_ROOT` fetches the recorded public kernel/module revisions and applies the local module compatibility patches. These scripts only build on the workstation; they do not flash a phone. The public wrappers have syntax checks, but a complete fresh build has not yet been repeated after packaging.

For Wi-Fi, build ruby conninfra/connfem with the WLAN gen4m and adaptor sources from pissarro-r-oss, applying the recorded compatibility patches. The tested combination uses SOC5_0 and `WLAN_CHIP_ID=6877`; using only a generic ARM WLAN build misses platform hooks. See `kernel/README.md`.

## 4. Assemble the native Linux boot chain

This stage needs a porter. Use the exact factory boot image as the packaging baseline, preserve its header/DTB/DTBO assumptions, replace its kernel and ramdisk with the built kernel and Halium early userspace, and configure Halium to mount the prepared Linux rootfs from userdata. Keep the device's vendor/system compatibility material required by the Android hardware container. Refer to upstream Droidian instructions rather than copying another phone's boot image.

On this device, **`fastboot boot` crashed the LK bootloader**. The working experiment used an image written to **boot_a** followed by reboot, with a correctly sized **128 MiB** boot image and an AVB footer, retaining the top-level factory vbmeta flags. The known working image used a test-key AVB footer; an unlocked bootloader is required. Image hashes in the manifest are identification records, not files offered for download.

There is intentionally no automated flash or partition-format command in this repository. A reusable initramfs/rootfs image builder and a second-device clean-install test are still required before an installable release. Do not use the old experimental automatic stock-boot recovery approach: after userdata is ext4 Linux data, stock Android boot alone cannot restore the device.

## 5. Prepare storage and accounts

The working layout is ext4 userdata labelled NASDATA with a 16 GiB rootfs image, `/DATA` pointing to `/userdata/DATA`, Docker under `/userdata/docker` and containerd under `/userdata/containerd`. Keep application data outside the rootfs image. Never format a guessed `/dev/sd*` path: resolve the userdata partition by its by-name link and verify its size and exact device identity first.

Create your own Linux user and password, fresh SSH host keys and a new SSH authorization key. Do not reuse any preconfigured rootfs from another person's phone. Configure Wi-Fi with NetworkManager locally; no Wi-Fi credentials are included here.

The kernel module overlay used by Droidian is `/usr/lib/droid-vendor-overlay/lib/modules`. Install modules with the matching kernel ABI and keep the original vendor partition read-only. Radio firmware comes from your legally obtained matching device firmware; it is not redistributed here.

## 6. Install Docker and Homeio

Use Docker's ARM64 Debian installation instructions, then validate `docker run --rm hello-world`. Confirm cgroups, namespaces, overlayfs and networking work with this vendor kernel. Record versions instead of assuming that a future newest runtime will still support a 4.19 kernel.

The tested Homeio version is **v1.10.3**, installed natively at `/opt/home-server`, with Node 22.23.4, Go 1.27.3, PostgreSQL 17 and nginx. The normal PC installation's generic OS overlay must not replace Droidian's vendor, NetworkManager, USB and logind configuration. The archived reviewed installer functions and phone-specific wrapper are in `homeio/installer/`; review them before using them, and satisfy prerequisites listed there.

Create a fresh Homeio account using its first-run web page. Enable Homeio, its upload/DBus helpers, nginx and Docker at boot. Homeio should run in the background; no browser kiosk is needed on the phone. A normal Phosh session remains available for local diagnostics.

## 7. Apply NAS-specific adaptations

On the phone, from a local copy of this repository:

```sh
sudo bash scripts/install-phone-adaptations.sh YOUR_LINUX_USER
```

This installs the display wake bridge and CPU policy, configures the 15-second display timeout, and disables the mobile-power-saver service-freezing behavior that otherwise stops NAS services with the screen off. It masks full sleep/hibernate targets so only the display sleeps. Use it on this port, after reviewing its changes; it is not a generic battery-saving setup.

To restore the power settings, retain the backup path printed by the script. Homeio hardware-reporting patches are separate and described in `homeio/README.md`.

## 8. Applications and validation

Install ARM64 applications. For Jellyfin, remove optional Raspberry Pi GPU device mounts; see `apps/jellyfin/README.md`. Do not grant privileged mode to work around missing hardware.

Complete [VALIDATION.md](VALIDATION.md), including Wi-Fi reconnect, restart, API/HTTP access with the display off, and real data transfer. The original experiment is not a substitute for a backup of important files.

## Recovery

Keep the matching full Xiaomi firmware and original partition backups off the phone. Linux uses userdata; restoring only Android boot after that conversion is insufficient. Recovery may require returning the complete device to factory layout and erasing userdata. The working project used a separate Halium diagnostic environment to regain access during port development. A redistributable rescue package is not included in this release.
