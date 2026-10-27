# Performance and stability baseline — 27 October 2026

The project device now runs a native Mali Vulkan path for the experimental ARMSX2 core, accessed through Homeio and streamed to the TV with Sunshine/Moonlight. The owner reported a substantial improvement over the first PS2 tests and accepted this version as the current baseline. Occasional short audio/video pauses remain. This is a result for one tested workload, not a promise that every PS2 game runs at full speed.

## Changes retained

| Change | Purpose and scope |
| --- | --- |
| Host-cached Vulkan readback | Reduce the CPU cost of transferring a rendered image to the X11 display. GPU fences and explicit cache invalidation remain in place. |
| EE placement on the two Cortex-A78 cores | Keep the main PS2 emulation task on the faster CPU tier, while leaving other tasks to their existing scheduling policies. |
| Coalesced duplicate callbacks | Avoid presenting the same image repeatedly while waiting for a new asynchronous core frame. The polling wait is bounded and yields between attempts. |
| Routine kernel diagnostics lowered to dynamic debug | Remove three noisy normal-path log sites without removing DMA cache synchronization or genuine fault handling. |
| Production post-boot logging policy | Reverse the vendor engineering rule that enables MediaTek debug verbosity. Console level 5 retains warnings/errors; the kernel ring buffer and journal remain available. |
| USB serial getty configuration | Avoid terminal reset/hangup and terminal-size auto-detection on ttyGS0, which could block normal shutdown/reboot. |

The adapters are in [apps/retroarch/native](../apps/retroarch/native/README.md). The source logging patch and reviewed runtime configuration are in [kernel](../kernel/README.md).

## What the measurements establish

- A 1280×720 synthetic changing-colour presentation check passed all 299 checked frames. Mean presentation time was approximately **8.85 ms before and 4.56 ms after** host-cached readback. This is a presentation-stage measurement, not a game FPS score.
- An isolated asynchronous-core test reduced display callbacks from **241 to 58** over approximately one second while preserving new frames. A stopped-frame producer returned within the bounded wait; the opt-out path was also tested.
- Live PS2 windows after tuning produced approximately **47.7–48.0 thousand audio frames/s**, against a 48 kHz target. The owner confirmed fewer pauses on the TV. Scenes differed between observations, so the before/after figures are not a matched replay benchmark.
- The EE placement, restoration on unload, narrower-mask handling and opt-out passed isolated-thread tests. The policy was then observed automatically after a full RetroArch reopen.
- Two ordinary warm reboots completed without manual recovery after the ttyGS0 workaround, with NAS-service recovery in approximately 76–82 seconds. A battery-disconnected cold boot was not tested.
- Native GLES/Vulkan probes and a 60-frame synthetic Jellyfin hardware decode → Mali resize → H.264 encode check passed after the kernel update. These tests do not certify every codec or core.

The TV stream used **1280×720 at 30 fps** with Sunshine software H.264 encoding. Sunshine already used ARM NEON. Jellyfin's separate MediaTek video bridge does not automatically accelerate Sunshine.

## Temperature and remaining limits

Sustained PS2 emulation and software streaming heated the CPU sensor to approximately **76–77 °C**. The thermal governor reduced the allowed Cortex-A78 frequency to **1.9–2.15 GHz**, below its 2.6 GHz factory maximum. Battery readings during those observations were around 40 °C; they are a different sensor.

Thermal protection, automatic voltage control and factory operating points were preserved. No overclock was applied. Cooling has not yet been compared under the same game scene. Better sustained cooling may restore frequency headroom, but the game-performance gain must be measured; frequency ratios are not FPS predictions.

The accepted baseline retains occasional microstutters. Further tuning is deferred until the cooling setup can be evaluated. The source update does not turn the existing clean-image candidate into a newly validated release; independent clean installation and image integration remain pending.

No game files, BIOS, saves, game titles, gameplay captures, device credentials or raw session logs are part of these validation notes.
