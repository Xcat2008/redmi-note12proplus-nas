# Native power-profile adaptation

Upstream: **Mobile Power Saver**, by **Cédric Bellegarde** and contributors. Source: [droidian/mobile-power-saver](https://github.com/droidian/mobile-power-saver), revision `477f4f666528a3ccdb45d6549e669019304a338e`, matching the installed 0.9.7 build. Its source and modifications retain **GPL-3.0 (upstream COPYING)**; the original license is in [COPYING.mobile-power-saver](COPYING.mobile-power-saver).

The patch fixes the balanced CPU baseline, the standard D-Bus profile setter and a screen-dozing override. CPU baseline/dozing changes are gated by `REDMI_NAS_MODE=1`. It also stores and restores profile selection. It does not alter operating-point tables, voltages or thermal controls. See [behavior and measurements](../../docs/ENERGY.md).

`source-lock.json` records the immutable source revision, archive and patch digests, and the tested ARM64 binary fingerprint. `scripts/install-energy-profiles.sh` verifies the inputs and either installs that precompiled image payload or builds the native system daemon from the matching source. The upstream package executable stays intact; activation uses the included launcher and a local D-Bus service override.

The native tests exercised all three profiles, property/governor consistency, saved selection across power-daemon reactivation, rejection of an invalid profile and resistance to the screen-off little-cluster override. Homeio checks the adapted service version before enabling its controls.
