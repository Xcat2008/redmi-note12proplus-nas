# Homeio adaptations

Upstream: https://github.com/doctor-io/homeio · baseline v1.10.3 · AGPL-3.0-only.

`arm-hardware-reporting.patch` changes hardware collection/contracts/UI. Copy `new-files/` into a clean v1.10.3 checkout, then run `git apply --check` and `git apply` on the patch before building. It reports heterogeneous ARM cores, physical versus Linux-usable/reserved memory, onboard RAM and the Mali GPU from device-tree/sysfs instead of assuming a PC DIMM/PCI layout.

The new reader has four fixture tests. On the working device those tests, ESLint, the Next.js production build and the server TypeScript build passed. Build in a staging checkout with constrained parallelism on this phone; keep the running installation and account database intact until the build succeeds. This package does not automatically replace a live Homeio installation.

`installer/` archives the reviewed upstream installer functions plus the phone-specific installation sequence. The generic PC OS overlay is deliberately skipped so Droidian networking, vendor integration and logind survive. The wrapper expects an already working systemd/Droidian port, Docker, apt and network access; install prerequisites include git, curl, certificates, build tools, nginx, Avahi, Samba and PostgreSQL support. It creates a fresh Homeio environment and refuses an existing `/opt/home-server`. Review its dependency requirements and upstream changes before use. The wrapper was made path-portable for publication but has not been re-run on a fresh device.

## Persistent Jellyfin catalog compatibility

Apply `jellyfin-hardware-compat.patch` to the same v1.10.3 checkout and copy its two new files from `new-files/`. This adds a narrowly scoped compose-materialization hook. It reads `/etc/homeio/hardware-profile`; only the explicit `redmi-ruby-nas` profile and the normal Jellyfin app/known Jellyfin image names enable software video mode. Raspberry Pi GPU device nodes and the Broadcom library mount are removed each time the stack is rendered. Other apps/devices and the NVIDIA variant are unchanged.

Run `node --import tsx --test lib/server/modules/docker/compose-hardware-compat.test.ts` for the six regression cases. The full ESLint, Next production build and server TypeScript build also passed on the working device. Build/deploy the patched Homeio; setting the profile file by itself does not modify an unpatched installation. A future upstream Homeio replacement needs the patches reapplied or merged upstream.

This fixes fresh installs after uninstalling, rather than relying on a manually edited installed compose file. Installation settings and media remain in their normal application data directories.
