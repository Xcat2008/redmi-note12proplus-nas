# Validation checklist

The working device passed these checks on 26 October 2026. Public wrapper scripts still require an independent clean-install test.

1. `uname -r`: `4.19.191-g914ba8403bb3`; PID 1 is systemd.
2. All eight CPUs online; two cpufreq policies use schedutil, with cluster maxima 2.0 / 2.6 GHz.
3. GPU sysfs identifies Mali-G68, and the compositor logs show actual GLES rendering.
4. Homeio, nginx, PostgreSQL, Docker, upload and DBus helpers are active after reboot.
5. A native ARM64 Docker container runs successfully.
6. Wi-Fi reconnects automatically; access works over LAN independently of the USB cable.
7. Wait at least 65 seconds with the display off. Repeat HTTP requests to Homeio; NAS service cgroups must remain unfrozen (`cgroup.freeze=0`).
8. Physical power off/wake and volume buttons work. Display timeout is 15 seconds; full-system suspend is disabled for NAS service availability.
9. Restart the phone and repeat LAN, service and display-off checks. On the original device the NAS services started before the mobile UI finished loading.
10. Check RAM with `free -h`; use MemAvailable for available memory. Kernel-reserved memory and filesystem cache are not a memory leak.

## Jellyfin result

The catalog download succeeded, but its compose template tried to mount `/dev/vcsm`, `/dev/vchiq`, Raspberry Pi video nodes and `/opt/vc/lib`. Docker rejected the missing hardware. Removing these optional device mappings and the Broadcom library mount allowed the ARM64 container to start. Homeio's installation operation completed and the Jellyfin web page returned HTTP 200; `/health` returned `Healthy` from another computer on the LAN.

The permanent Homeio materialization hook then passed six regression tests, ESLint, a full Next production build and the server TypeScript build. Two uninstall/install cycles using the untouched catalog source passed, preserving application data (`removeVolumes=false`); Jellyfin became Healthy after both. Media playback, hardware transcoding and external-disk libraries remain untested. The Homeio app-store catalog is not universally certified for the phone: each app's CPU architecture, devices, permissions and power requirements need checking.

## Not yet established

- Hub host-mode operation with simultaneous PD charging.
- External Ethernet and three external disks, including drive spin-up power.
- SMB throughput and sustained real file-transfer checks.
- Bluetooth, SIM/mobile data and camera functionality.
- A public image reproducibly installed on a second clean device.
