# Hardware and compatibility

Tested device: **Redmi Note 12 Pro+ 5G, 22101316UG / rubypro**, MediaTek MT6877 / Dimensity 1080. The initial Android firmware was OS2.0.16.0.UMOEUXM. This is not a test of every device sharing the ruby family name.

| Component | Verified result / limit |
| --- | --- |
| CPU | 8 online physical cores: 6 Cortex-A55 up to 2.0 GHz + 2 Cortex-A78 up to 2.6 GHz; no SMT |
| CPU policy | Balanced uses schedutil on both clusters; persistent Homeio profiles and the native power-service correction retain factory limits and thermal protection |
| RAM | 8 GiB physical; Linux MemTotal approximately 7.3–7.4 GiB because of reserved memory. Shared GPU memory is not extra RAM. |
| GPU | ARM Mali-G68 MC4, real OpenGL ES 3.2 rendering in Phoc. It is not NVIDIA. |
| Display | 1080 × 2400, mobile UI scale 3; a wake bridge reapplies vendor brightness after DPMS wake |
| Internal storage | 256 GB nominal; approximately 221 GiB ext4 data filesystem. NAS base rootfs: 16 GiB; the experimental KVM runtime was expanded to 32 GiB. Candidate sizes remain defined by their own manifest. |
| Wi-Fi | Working and reconnects automatically after reboot |
| USB | High-speed USB 2.0 observed. External Ethernet and storage share that bus. |
| Wired video | Do not expect HDMI from a USB-C hub; this phone has no supported wired video output. |
| Charging + USB host | Not yet validated with the intended hub and native Linux |
| Bluetooth | HIDL/VHCI bridge working; Homeio radio power, discovery and automatic scan timeout tested in the browser; physical controller pairing remains untested |
| KVM / Proxmox | Tested experimental EL2/kernel profile; full Debian ARM64 VM using all eight physical CPUs. Separate from the current clean image candidate; see [scope](PROXMOX.md). |
| SIM / modem / mobile data | Not validated |
| Cameras | Not validated; not a goal of this NAS build |
| Video acceleration | H.264 / HEVC / VP9 8-bit SDR hardware decode, Mali resize and H.264 hardware encode verified; other video paths may use CPU |

The planned hub is an ICY BOX IB-DK4034a-CPD with a USB-C PD charger and three SATA 2.5-inch disks. These are planned accessories, not certified compatible hardware. Power available to each USB port and mechanical-disk spin-up current must be checked in a physical test. A 3.5-inch HDD requires an enclosure/adapter with its own suitable power supply.

Reference specifications: [Xiaomi](https://www.mi.com/gr/product/redmi-note-12-pro-plus-5g/specs/), [MediaTek](https://i.mediatek.com/dimensity-1080), [Xiaomi USB / video FAQ](https://www.mi.com/jp/support/faq/details/KA-399147/).
