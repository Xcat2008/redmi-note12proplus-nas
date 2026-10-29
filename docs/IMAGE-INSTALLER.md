# Clean image and installer / Imagem limpa e instalador

## Current state

A clean candidate has been assembled separately from the author’s working NAS. It consists of an Android-format `boot.img`, a sparse `userdata.img`, and a Windows installer. A phone does not boot a PC-style ISO.

**The candidate has not passed a complete clean physical installation test. It is not a stable release or a public ready-to-flash download.** The existing phone has not been erased to produce it. Source and documentation are public so the work can be reviewed while validation continues.

| Check | State |
| --- | --- |
| Fresh upstream Droidian base, verified archive digest | Prepared |
| Author accounts, Wi-Fi profiles and SSH host keys excluded | Audited offline |
| Android sparse image structure and file digests | Checked offline |
| MediaTek video adapter and automatic Jellyfin profile | Compiled into the clean candidate; full video chain tested on the running device |
| RetroArch in Homeio, Ozone and native Mali rendering | Tested on the running device; included in the next candidate's setup |
| Sunshine | Shared streaming service with separate RetroArch and Steam launch entries; exercised through Moonlight on the project device |
| Steam Big Picture | Official native ARM64 download on first setup, Mali composition, update restart and program recovery included |
| Bluetooth controls in Homeio | First-setup source included; authenticated controls and Xbox pairing/navigation exercised on the project NAS |
| CPU energy profiles | Corrected native power manager and Homeio controls included; factory CPU/GPU/memory scaling tested on the running device |
| Per-installation Linux PIN and SSH key | Implemented; no shared default credentials |
| Windows installer | Graphical assistant and CLI built; candidate installation remains blocked, verification does not contact the phone |
| Model, unlocked bootloader, slot and partition-layout checks | Implemented |
| Proxmox / eight-CPU KVM profile | Tested on the configured device. Absent from rc7; the next 0.2 candidate preloads clean userspace and matching KVM modules, disabled by default. Fresh EL2 activation and installation remain unvalidated. |
| Clean physical install, Wi-Fi onboarding, first NAS setup | Pending |
| Complete binary redistribution and corresponding-source audit | Pending before public binaries |

The rc7 integration consolidates the current native gaming, mobile telemetry,
optional memory/battery controls, Wi-Fi scan compatibility, quiet GPU logging
and USB console reboot fix. Its Homeio overlay was built from a fresh v1.10.3
checkout. The distribution Mali backend passed device creation, synthetic-frame
presentation and window resizing on the actual GPU. The accepted emulator bridge
is retained unchanged. See [the validation scope](NATIVE-GAMING.md); no live user
installation is erased to produce or audit the candidate.

The candidate includes `/usr/local/lib/redmi-nas/mediatek`, its source, startup profile and the Homeio installation hook. New installations receive the hardware video bridge, persistent Bluetooth adaptation and RetroArch profile automatically; no personal Jellyfin account, copied library, controller pairing or media file is included. The video bridge uses MediaTek decoding and encoding with Mali resizing for the tested SDR formats.

The gaming setup installs RetroArch and Sunshine as a Homeio-managed stack during the internet-connected first setup. It downloads pinned upstream packages and builds the local container image. Homeio's normal context menu starts, stops or uninstalls the stack. The phone's application menu is not used for this workflow. The native renderer uses Mali; browser capture and Sunshine currently encode video on the CPU. See [the gaming integration](../apps/retroarch/README.md).

The target is specifically **22101316UG / rubypro, 256 GB**, using the documented factory firmware **OS2.0.16.0.UMOEUXM** and slot **a**. This is not an image for the 4G model, another Redmi, or an arbitrary partition layout.

## Proxmox image boundary

The [experimental KVM/Proxmox profile](PROXMOX.md) was validated after **0.1.0-rc7** was assembled. The next **0.2.0-rc1** build adds a clean Proxmox package base, the eight-CPU cache adapter, UEFI adaptation and matching KVM kernel/modules. Its optional service starts disabled, with no author password, account database or VM. It is a separate validation candidate, not a public approved replacement for rc7.

The normal NAS installer does not activate EL2 or change the phone's partition metadata. A fresh device without actual EL2 cannot use hardware KVM merely because the new kernel and packages are present. `setup-preloaded.py` checks that capability before starting the optional environment; `prepare-profile.py` stages only separate, unpersonalized build roots. These helpers do not make the whole fresh platform installation validated.

Proxmox is proposed as an optional component for the next compatible profile. A fresh image must be rebuilt from clean sources, receive individual setup credentials and pass the platform activation, clean-install and full-phone-reboot checks before it can be described as preinstalled. None of the candidate's physical-validation or redistribution flags has been enabled by the source publication.

## Intended installation flow

1. Back up the phone and unlock its bootloader using Xiaomi’s official process. This remains a manual Xiaomi-account step.
2. Start from the documented matching factory firmware, with an appropriate recovery plan.
3. Extract a tested release, connect the phone in FASTBOOT and start the installer.
4. The installer verifies checksums and the device. Installing requires explicit confirmation that the phone will be erased.
5. Choose a personal Linux/unlock PIN. The computer generates a new SSH key; the private key stays on that computer.
6. Complete one-time setup over the physical USB connection and configure Wi-Fi.
7. Once internet is available, first-boot services install the pinned NAS stack. Open Homeio from another computer and create a separate web account.

The graphical assistant blocks installation until both the physical validation and binary redistribution checks pass. Its CLI expert override is for supervised testing, not a recommended shortcut. The 0.2 test profile also checks and supplies Linux AVB metadata for the unlocked bootloader; this change still needs physical first-install validation. See the [complete Windows user guide](INSTALL-WIZARD.pt-PT.md).

## Source

The guarded client and one-time USB setup handler are in [`image/`](../image/). They do not contain the author’s passwords or keys. The client is an installation tool, not an alternative to Xiaomi’s bootloader unlock or a universal Android installer.

## Português

A imagem limpa já foi construída, juntamente com o instalador Windows. Ainda falta repetir o processo completo num telemóvel limpo e concluir a revisão de redistribuição dos binários. Até lá, a publicação apresenta o código e o estado real dos testes. O desbloqueio Xiaomi continua a ser manual; a instalação apaga o aparelho e cada utilizador define as suas próprias credenciais.
