# Kernel and connectivity sources

The kernel starts from the public ruby-s-oss revision in `sources.lock.json`; the supplied resolved NAS config enables namespaces/cgroups, overlayfs, USB gadget ACM/RNDIS, UAS and other Linux features. Camera entries that did not exist in the public source were excluded while preparing the original config. Camera support is not claimed.

`wlan-ruby-compat.patch` is the tracked source diff against the pinned pissarro WLAN tree used by the working build. It adapts ruby conninfra address types, MT6877 QoS/platform APIs and public-source headers. It contains source changes only, not compiled modules or firmware.

Build the kernel first. The Wi-Fi modules use the exact same kernel output and symbol versions. The original module build used:

- ruby conninfra / connfem from `mtk-modules`;
- pissarro WLAN adaptor `CONNAC2X2_SOC5_0`, module name `wmt_chrdev_wifi`;
- patched gen4m with AXI HIF, `MTK_COMBO_CHIP=SOC5_0`, `WLAN_CHIP_ID=6877`, `MTK_ANDROID_WMT=y`, `MTK_ANDROID_EMI=y`;
- `KBUILD_EXTRA_SYMBOLS` containing conninfra, adaptor and connfem `Module.symvers`.

The source layout links `vendor/mediatek/kernel_modules` to ruby modules, with the WLAN gen4m path linked to the patched pissarro source. Use `scripts/build-connectivity-modules.sh` after conninfra has been built for this output; the wrapper deliberately checks for its `Module.symvers` rather than pretending an incomplete module build is ready. A fully automated fresh connectivity build is still pending.

Kernel/module material retains GPL-2.0-only and upstream per-file notices. The public host wrappers have syntax checks; this package has not yet been rebuilt from an entirely empty build directory.

## Later stability baseline

The tested follow-up changes three routine GPU/ION log sites with `quiet-normal-gpu-sync.patch`. [Runtime policies](runtime/README.md) address the vendor debug override and ttyGS0 shutdown stalls. The existing kernel configuration and exported module CRC table were retained. These sources are documented separately from the original image candidate; see [validation limits](../docs/PERFORMANCE.md).
