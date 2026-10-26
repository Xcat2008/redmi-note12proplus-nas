# Homeio adaptations

Upstream: https://github.com/doctor-io/homeio · baseline v1.10.3 · AGPL-3.0-only.

`arm-hardware-reporting.patch` changes hardware collection/contracts/UI. Copy `new-files/` into a clean v1.10.3 checkout, then run `git apply --check` and `git apply` on the patch before building. It reports heterogeneous ARM cores, physical versus Linux-usable/reserved memory, onboard RAM and the Mali GPU from device-tree/sysfs instead of assuming a PC DIMM/PCI layout.

The new reader has four fixture tests. On the working device those tests, ESLint, the Next.js production build and the server TypeScript build passed. Build in a staging checkout with constrained parallelism on this phone; keep the running installation and account database intact until the build succeeds. This package does not automatically replace a live Homeio installation.

`installer/` archives the reviewed upstream installer functions plus the phone-specific installation sequence. The generic PC OS overlay is deliberately skipped so Droidian networking, vendor integration and logind survive. The wrapper expects an already working systemd/Droidian port, Docker, apt and network access; install prerequisites include git, curl, certificates, build tools, nginx, Avahi, Samba and PostgreSQL support. It creates a fresh Homeio environment and refuses an existing `/opt/home-server`. Review its dependency requirements and upstream changes before use. The wrapper was made path-portable for publication but has not been re-run on a fresh device.

## Persistent Jellyfin catalog compatibility

Apply `jellyfin-hardware-compat.patch` to the same v1.10.3 checkout and copy its two new files from `new-files/`. This adds a narrowly scoped compose-materialization hook. It reads `/etc/homeio/hardware-profile`; only the explicit `redmi-ruby-nas` profile and the normal Jellyfin app/known Jellyfin image names enable software video mode. Raspberry Pi GPU device nodes and the Broadcom library mount are removed each time the stack is rendered. Other apps/devices and the NVIDIA variant are unchanged.

Run `node --import tsx --test lib/server/modules/docker/compose-hardware-compat.test.ts` for the six regression cases. The full ESLint, Next production build and server TypeScript build also passed on the working device. Build/deploy the patched Homeio; setting the profile file by itself does not modify an unpatched installation. A future upstream Homeio replacement needs the patches reapplied or merged upstream.

This fixes fresh installs after uninstalling, rather than relying on a manually edited installed compose file. Installation settings and media remain in their normal application data directories.

## Bluetooth controllers from the web desktop

`bluetooth-settings.patch` adds a Bluetooth section to Settings. Copy its implementation from `new-files/`, apply the patch to the pinned Homeio release and rebuild. It uses the NAS system BlueZ service through D-Bus; it does not use the browser computer's Bluetooth adapter.

The panel can switch the radio on/off, search for 45 seconds, pair a selected controller, connect, disconnect and forget it. Its pairing agent belongs only to that D-Bus connection and accepts requests only for the selected device during an active pairing operation. It does not replace Phosh's default agent or make the NAS discoverable. Pairing requires automatic controller pairing; PIN-entry accessories are outside this panel's scope.

All endpoints require a Homeio session. Mutations also require a matching browser origin. Device addresses are validated and resolved against BlueZ's current device objects; the API never executes shell commands. Scan sessions and pairing attempts have bounded lifetimes. Six service tests cover validation, discovery lifetime, agent selection, pairing timeouts and device lifecycle:

```sh
node --test lib/server/modules/bluetooth/service.test.mjs
```

Physical Xbox/PlayStation pairing and in-game input remain separate validation steps. For Moonlight on a TV, connect the controller to that TV; its input reaches Sunshine over the streaming connection. See [Bluetooth setup](../docs/BLUETOOTH.md).

## Native energy profiles

Apply `energy-profiles.patch` after the Bluetooth patch and copy its implementation from `new-files/`. Settings gains a Performance section with the three native CPU profiles, live cluster governors, GPU telemetry and physical/usable/available RAM. The adapted native power service must be installed through `scripts/install-energy-profiles.sh`; changing a UI label alone does not change CPU behavior.

The API requires a session and a matching origin for mutations. It accepts only Power saver, Balanced and Performance and verifies the resulting CPU governors. Overclock controls remain disabled because above-stock operating points have not been validated. Three parsing/validation tests and native/browser profile checks passed. See [energy behavior and tests](../docs/ENERGY.md).
