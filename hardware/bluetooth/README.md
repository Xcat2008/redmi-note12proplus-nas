# Bluetooth adaptation

The bridge is based on [mer-hybris/bluebinder](https://github.com/mer-hybris/bluebinder). The exact upstream commit and source checksum are recorded in `upstream.json`. Its original authors and GPL-2.0-or-later license are retained.

This device uses the vendor HIDL Bluetooth HAL. The adaptation accepts the real HCI index from VHCI when the kernel has no rfkill interface. It does not invent an rfkill device or embed a Bluetooth address. A narrowly scoped feature mask disables the synchronization-train capability that this firmware advertises but rejects; Secure Connections remains available.

The image also includes `hci_vhci` and `hidp` modules built against the exact documented kernel. UHID, generic HID and Microsoft HID support are already built into that kernel. The stock post hook is bypassed because the controller supplies its own factory address and the hook depends on unavailable Android properties.

Validation covers controller registration, power off/on, discovery startup and service restart. Physical pairing, Xbox input and Bluetooth audio still require tests with the relevant devices.

To rebuild the userspace bridge on the documented ARM64 Debian base, install `build-essential`, `libgbinder-dev`, `libglib2.0-dev` and `libsystemd-dev`, then compile:

```sh
cc -O2 -g0 -Wall -DUSE_SYSTEMD=1 -DNAS_HIDL_ONLY=1 \
  -o bluebinder-nas bluebinder.c \
  $(pkg-config --cflags --libs libgbinder glib-2.0 libsystemd)
```

The modules use the kernel source, configuration, toolchain and `Module.symvers` identified in [the kernel documentation](../../kernel/README.md). Build `drivers/bluetooth` with `CONFIG_BT_HCIVHCI=m` and `net/bluetooth/hidp` with `CONFIG_BT_HIDP=m`; retain the existing kernel configuration. Do not substitute modules from another kernel.
