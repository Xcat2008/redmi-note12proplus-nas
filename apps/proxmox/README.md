# Proxmox ARM64 integration

**Experimental source preview, tested on the project phone. This component is not in the current clean image candidate.**

The running Redmi has Proxmox VE 9.2.20 in an isolated `systemd-nspawn` environment. Its Linux guests use hardware KVM and can execute on all eight physical cores. The source here preserves the compatibility changes without distributing a configured phone, accounts, virtual disks or firmware binaries.

Read the [installation boundary, architecture and validation](../../docs/PROXMOX.md) first. Installing the Proxmox packages does not enable EL2 or turn the existing NAS candidate into a KVM image.

The next 0.2 validation candidate stages clean packages with `prepare-profile.py` and includes the guarded `setup-preloaded.py` helper. They preserve an existing NAS/account database, leave the PVE service disabled by default and do not activate EL2. The complete fresh-device installation and full phone reboot still need validation; these helpers are not a released one-click platform installer.

## Included

| File | Purpose |
| --- | --- |
| `runtime/redmi-kvm-cache-affinity.c` | Keeps only the legacy cache-description KVM ioctls on a consistent A78 CPU; normal guest execution remains free to use the eight CPUs |
| `runtime/kvm-launcher.sh` | Loads that compatibility library for the isolated QEMU launcher, preserving its original executable and argv |
| `runtime/refresh-cache-compat.py` | Restores the launcher after package maintenance |
| `runtime/firmware_compat.py` | Checks the known EDK2 code image and avoids its failing early identity map; the original package file is retained |
| `runtime/Drive.pm` | Uses the normal non-io_uring disk fallback on the old phone kernel |
| `runtime/ProcFSTools.pm` | Identifies the heterogeneous CPU layout and handles the unavailable CPU-full PSI counter; memory/load scoping still requires LXCFS |
| `validation.json` | Sanitized functional-test scope and remaining limits |
| `apply-existing.sh` | Guarded maintenance of an existing compatible Proxmox environment; not a fresh NAS or platform installer |

## Existing-profile maintenance

These commands run **inside an already functioning isolated Proxmox environment**, with the tested KVM kernel and exact hardware. They must not run on the NAS host. The default action checks without changing configuration:

```sh
bash apps/proxmox/apply-existing.sh --check
```

To apply the source integration, stop the VMs first and ensure `build-essential` is available in this environment. The explicit apply step compiles the adapter, preserves vendor files with `dpkg-divert` and installs the update hooks:

```sh
sudo bash apps/proxmox/apply-existing.sh --apply
```

Restart only the Proxmox environment from the NAS host, then repeat the guest tests in the guide. The public updater has offline regression checks and its non-installing preflight was exercised on the configured device; it has not been replayed as a complete fresh installation. It does not create the container, reserve networking, add a Homeio shortcut, create an account, change CPU/RAM limits, activate EL2 or install a kernel.

If the preflight rejects the environment, do not bypass it by changing version strings. The missing platform/install stages are still separate work for the next image profile.

## Licensing

Original integration: José Miranda (Xcat2008), Portugal. The small cache adapter, QEMU launcher and firmware compatibility helper have MIT notices; other integration files use AGPL-3.0-only. The PVE modules load the original, separately installed vendor modules. Proxmox, QEMU, Linux/KVM, LXCFS and EDK2 retain their respective upstream licenses and authorship. No third-party binary is bundled here.
