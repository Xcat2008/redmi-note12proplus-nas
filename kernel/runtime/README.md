# Runtime stability configuration

These files document the policies exercised on the configured project device. They are not an automatic kernel flash or an installation script for other phones.

`20-gpu-diagnostics.conf` and `30-console-verbosity.conf` are additive drop-ins for `android_boot_completed.service`. Their Python helpers belong in `/usr/local/lib/redmi-nas/` and run after the vendor boot-completion rule. The debug helper is scoped to dynamic debug calls; source-level warnings/errors and GPU fault paths are retained. The console helper suppresses routine notice/info/debug console output while retaining warnings/errors and leaving the kernel ring buffer/journal unchanged.

`serial-getty-nonblocking.conf` is a drop-in for `serial-getty@ttyGS0.service`, not for all serial terminals. The fixed 24×80 dimensions avoid size auto-detection; TTYReset and TTYVHangup are disabled on this USB gadget instance. The warm-reboot recovery was tested twice on the project device. See [systemd issue 37854](https://github.com/systemd/systemd/issues/37854).

The companion `../quiet-normal-gpu-sync.patch` changes only three ordinary log statements in the pinned ruby kernel tree. Cache synchronization, normal control flow and primary error paths are unchanged. Rebuild with the matching configuration and module symbol versions; do not apply a boot image intended for a different device.
