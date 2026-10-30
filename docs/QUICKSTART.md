# Start here / Começar aqui

The [experimental 0.2.0-rc3 release](https://github.com/Xcat2008/redmi-note12proplus-nas/releases/tag/v0.2.0-rc3) provides a Windows downloader and installation assistant. Start with the [Portuguese installation guide](INSTALL-WIZARD.pt-PT.md); the engineering porting notes are optional background, not steps that every user needs to perform.

1. Confirm **Redmi Note 12 Pro+ 5G 22101316UG / rubypro / 256 GB**, factory firmware **OS2.0.16.0.UMOEUXM**, slot **a**. Other models and capacities are not validated.
2. Back up what you need and unlock the bootloader through Xiaomi. Complete any owner-account activation. The installer does not replace Mi Unlock.
3. Download **RedmiNAS-Download.exe** from the release. It downloads and verifies the fixed parts, joins the ZIP and opens **RedmiNAS-Setup.exe**.
4. Verify the package, choose individual credentials and optional Wi-Fi, connect only the target phone in FASTBOOT and read the erase confirmation. Installation replaces Android and data. Do not use it as an upgrade for an existing NAS.
5. Keep USB, power and Internet available during personalization and first setup. Open **http://redmi-nas.local** or the phone's router-assigned address and create your Homeio account.
6. Add your own media and applications. Jellyfin's MediaTek profile is applied through the store. The gaming setup includes RetroArch, Steam and Sunshine; upstream accounts are yours to configure.

The boot/layout was physically validated with rc2; changed rc3 userspace was exercised on the project NAS. A new complete physical rc3 installation and a second-device test were not performed. See [the exact image scope](IMAGE-INSTALLER.md).

## Optional virtualization

Proxmox is preloaded as a clean, disabled optional base. Homeio Settings checks KVM before setup. It needs EL2/KVM already available; Xiaomi bootloader unlock alone is insufficient, and stock-device EL2 activation is not automatic in this release. NAS use does not require Proxmox.

## Engineering references

[Installation and porting](INSTALLATION.md) · [Tested hardware](COMPATIBILITY.md) · [Native gaming](NATIVE-GAMING.md) · [Video acceleration](MEDIATEK-VIDEO.md) · [Credits](../CREDITS.md)
