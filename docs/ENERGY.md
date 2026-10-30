# CPU profiles and hardware scaling

Open **Settings â†’ Performance** in Homeio. The profile controls the native Droidian power service and is saved on the NAS.

| Profile | CPU behavior |
| --- | --- |
| Power saver | Requests the lowest factory CPU frequencies: 500 MHz on the six Cortex-A55 cores and 650 MHz on the two Cortex-A78 cores |
| Balanced | Default and recommended. `schedutil` adjusts both clusters with demand, up to their factory 2.0 / 2.6 GHz limits |
| Performance | Requests the highest factory CPU frequencies; thermal and platform power limits can still reduce them |

The GPU and memory retain MediaTek's automatic DVFS. No frequency table, regulator voltage or thermal limit is changed. The NAS remains reachable when its display turns off; full-system sleep remains disabled for server availability.

The balanced/performance boot policy also checks CPU availability. On the tested
kernel, it can bring the two A78 CPUs back online if they were left offline and
MediaTek reports no active thermal or battery-power restriction. It never disables
those restrictions or forces a core online against a kernel refusal. The power
saver profile is left alone. Online cores can still idle and scale their clocks;
availability does not mean they run continuously at maximum frequency.

A reported clock is not a power meter. Some driver readings show the last active frequency even while a core is in an idle state. An application rendering a menu or streaming video can also create work without keyboard or mouse input.

## Corrected power-service behavior

The installed Mobile Power Saver version could cache a boot-time `powersave` governor as its balanced default. Its standard `ActiveProfile` D-Bus setter also updated the reported profile without applying the CPU policy. A separate dozing path could request little-cluster power saving despite the NAS display-independent policy.

The pinned adaptation addresses these paths in the existing manager. In NAS mode, its balanced CPU baseline is `schedutil`; display dozing cannot override that profile when screen-off power saving is disabled. Profile selection applies to both CPU clusters, updates the D-Bus property and saves the choice. There is no second polling daemon fighting the original manager.

The distribution's `/usr/sbin/mobile-power-saver` remains intact. A side-by-side build is activated through `/usr/local/share/dbus-1/system-services/`; its launcher enables the adaptation only for the `redmi-ruby-nas` hardware profile. The installer verifies pinned source and patch digests. The clean candidate includes the tested ARM64 binary; source installations can build it locally.

## Measurements on the project phone

Tests on 26 October 2026 used factory operating points:

- Both clusters reached 2.0 / 2.6 GHz during a CPU workload. A six-second integer microbenchmark pinned to CPUs 0 and 6 completed approximately four times as many work blocks after the governor correction. Application gains depend on the workload.
- An offscreen OpenGL ES workload identified **ARM Mali-G68 MC4**, completed 276 frames in about eight seconds and reported no GL errors. GPU frequency rose from **385 to 950 MHz**, with observed load up to 96%.
- An eight-thread memory-copy probe used **512 MiB** and checked every byte of both buffers afterward. It completed without a data mismatch; the DDR controller reached the highest factory operating point in its table. This is a bounded copy/integrity probe, not an exhaustive test of all physical RAM.
- The highest observed CPU temperature across these short checks was approximately **70 Â°C**. Stock thermal control remained enabled. Sustained performance and power draw depend on load, cooling and charging conditions.
- All three native profiles applied to both clusters. The selected profile survived a restart of the native power daemon. Browser tests checked selection, reported governors, authentication and origin protection. A full phone reboot with this update remains a separate validation step.

The memory display distinguishes **8 GiB physical RAM**, roughly **7.4 GiB Linux-usable RAM** after platform reservations, and current available memory. ZRAM and filesystem cache are retained; they do not change the installed physical capacity.

## Operating limits

The web interface exposes the three factory-limit CPU profiles. Frequency tables, voltage management and platform thermal controls remain unchanged.

## Source and checks

- [Pinned Mobile Power Saver adaptation](../hardware/power/README.md)
- [Energy installer](../scripts/install-energy-profiles.sh)
- [Linux CPU frequency documentation](https://docs.kernel.org/admin-guide/pm/cpufreq.html)
- [Upstream Mobile Power Saver](https://github.com/droidian/mobile-power-saver)

On the patched Homeio checkout:

```sh
node --import tsx --test lib/server/modules/system/energy-profiles.test.ts
```
