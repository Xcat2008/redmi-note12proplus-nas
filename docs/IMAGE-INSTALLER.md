# Clean image and Windows installer

[Experimental 0.2.0-rc3 release](https://github.com/Xcat2008/redmi-note12proplus-nas/releases/tag/v0.2.0-rc3) · [Step-by-step guide](INSTALL-WIZARD.pt-PT.md)

The package targets Redmi Note 12 Pro+ 5G **22101316UG / rubypro / 256 GB**, factory firmware **OS2.0.16.0.UMOEUXM**, active slot **a**, and an already unlocked Xiaomi bootloader. It contains Android boot/data images, not a PC ISO. Installation erases Android and all user data. The person installing must confirm the model and firmware; the fastboot product alone does not identify every hardware variant.

## What the assistant does

The small release downloader retrieves fixed release parts, checks SHA-256, joins the ZIP and opens the assistant. The assistant checks image size, hashes and sparse structure before accessing a phone. It verifies one fastboot device, product, unlocked state, active slot and partition sizes, then requires explicit erase confirmation. Google Platform-Tools are downloaded only after approval if missing. Factory AVB metadata and GPT are preserved.

Physical USB onboarding sets an individual Linux PIN and SSH public key. The private key stays on the installer's PC. Internet-connected first setup installs Homeio and the gaming integration. Accounts for Homeio and upstream services are created by each user. No games, console BIOS, media, Steam sessions or author credentials are included.

## Validation scope

The rc2 supervised physical clean installation passed NAS bootstrap, network onboarding and full phone restarts with and without optional Proxmox. See [the rc2 record](../image/validation-rc2.json). The rc3 uses the identical boot image and layout; its userspace fixes were exercised on that running NAS. A new full physical rc3 reinstall, a second-device test and long-duration certification were not performed. The rc3 manifest keeps `physical_install_test_passed: false` and records the narrower rc2 baseline and live userspace validation explicitly.

The release includes the corresponding-source catalog for 1067 installed source versions, source parts, original package/license notices and hashes. Historical source descriptors were checked for exact source/version identity and file SHA-256; their DSC signatures were not independently revalidated. Components retain their original licenses, including the Genesis Plus GX restrictions documented in THIRD_PARTY_NOTICES.md.

## Optional virtualization

A clean Proxmox ARM64 userspace is preloaded but disabled, without author accounts or VMs. Homeio Settings checks real KVM before optional setup. This does not install a generic Proxmox kernel or replace the Android hardware container. The project phone already had EL2 prepared; stock-device EL2 activation is not automated by this release. Bootloader unlock alone is insufficient for hardware KVM. The NAS remains usable without Proxmox. See [Proxmox compatibility](PROXMOX.md).

## Graphics boundary

Native Steam composition and RetroArch presentation use Mali. Browser H.264 streaming has a MediaTek V4L2/ION adapter, measured around 30 FPS at 720p. X11 readback, Steam vector rasterization and other stages still use CPU. Sunshine encoding is a separate path. See [the tested MediaTek browser profile](SELKIES-MEDIATEK.md).

This package installs a fresh system; it does not preserve or upgrade an existing NAS. Read the recovery section in the installation guide before flashing. Do not use generic vbmeta images or relock the bootloader.
