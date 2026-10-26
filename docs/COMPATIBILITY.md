# Hardware and compatibility

Tested device: **Redmi Note 12 Pro+ 5G, 22101316UG / rubypro**, MediaTek MT6877 / Dimensity 1080. The initial Android firmware was OS2.0.16.0.UMOEUXM. This is not a test of every device sharing the ruby family name.

| Component | Verified result / limit |
| --- | --- |
| CPU | 8 online physical cores: 6 Cortex-A55 up to 2.0 GHz + 2 Cortex-A78 up to 2.6 GHz; no SMT |
| CPU policy | schedutil on both clusters; stock maximum frequencies and thermal limits retained |
| RAM | 8 GiB physical; Linux MemTotal approximately 7.3–7.4 GiB because of reserved memory. Shared GPU memory is not extra RAM. |
| GPU | ARM Mali-G68 MC4, real OpenGL ES 3.2 rendering in Phoc. It is not NVIDIA. |
| Display | 1080 × 2400, mobile UI scale 3; a wake bridge reapplies vendor brightness after DPMS wake |
| Internal storage | 256 GB nominal; approximately 221 GiB ext4 data filesystem; 16 GiB Linux rootfs image |
| Wi-Fi | Working and reconnects automatically after reboot |
| USB | High-speed USB 2.0 observed. External Ethernet and storage share that bus. |
| Wired video | Do not expect HDMI from a USB-C hub; this phone has no supported wired video output. |
| Charging + USB host | Not yet validated with the intended hub and native Linux |
| Bluetooth | Not working/validated: bluebinder reports a missing /dev/rfkill |
| SIM / modem / mobile data | Not validated |
| Cameras | Not validated; not a goal of this NAS build |
| Hardware video encoding | H.264 MediaTek VPU confirmed in Jellyfin/FFmpeg through the ION/DMA-BUF adapter; software decoding and scaling |

The planned hub is an ICY BOX IB-DK4034a-CPD with a USB-C PD charger and three SATA 2.5-inch disks. These are planned accessories, not certified compatible hardware. Power available to each USB port and mechanical-disk spin-up current must be checked in a physical test. A 3.5-inch HDD requires an enclosure/adapter with its own suitable power supply.

Reference specifications: [Xiaomi](https://www.mi.com/gr/product/redmi-note-12-pro-plus-5g/specs/), [MediaTek](https://i.mediatek.com/dimensity-1080), [Xiaomi USB / video FAQ](https://www.mi.com/jp/support/faq/details/KA-399147/).
