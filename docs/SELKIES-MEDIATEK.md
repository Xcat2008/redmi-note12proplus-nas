# MediaTek encoding for the browser session

The tested Redmi profile now connects Selkies/Pixelflux to the phone's MediaTek
H.264 encoder through V4L2 M2M. Steam still renders through its native Mali/ANGLE
Vulkan bridge. These are separate operations: rendering the application,
capturing its X11 window and encoding the picture sent to the browser.

The browser defaults remain **1280 × 720 at 30 FPS**. X11 capture and presentation
still copy pixels through shared memory; this is not an end-to-end zero-copy
pipeline. Steam's vector rasterization remains on the CPU to avoid the icon
corruption observed with forced GPU rasterization. Sunshine continues to use
software encoding; this change does not claim hardware encoding for Moonlight.

## Device adaptation

The [scoped adapter](../apps/retroarch/mediatek-pixelflux.c) is preloaded only in
the shared gaming container. It maps the tested driver's ION DMA-BUF interface
to Pixelflux's MMAP requests, translates its packed BGRA format name and maps the
sequence-header request to MediaTek's joined-header control. An explicit first
keyframe prevents the initial capture from timing out and reopening the encoder.
The selected H.264 level follows the frame size and rate.

The vendor's RGB conversion produces limited-range BT.601 but labels the SPS
matrix as BT.709. A bounded parser corrects only that existing matrix field,
without re-encoding frames or inserting missing metadata. It preserves the other
NAL units and leaves unrecognised parameter sets untouched.

The container receives `/dev/video2`, `/dev/ion`, the encoder's device group and a
read-only adapter mount. Native Steam's Mali libraries are not replaced. A
container without a DRI render node can still use this separate V4L2 video engine;
the useful stream statistic is the active **V4L2M2M H.264** encoder, rather than
the presence of a desktop GPU in a generic device-information label.

## Checks on the project device

On 30 October 2026, the adapter compiled with warnings treated as errors. Its
colour parser passed address/undefined-behaviour sanitizer checks, truncated-input
tests and bounded random-input tests. A synthetic coloured stream decoded with
the expected RGB values and carried SPS/PPS headers with each tested keyframe.
The same hardware path worked as the service's unprivileged user.

A capture of the running Steam display produced **450 frames in 15.081 seconds**,
about **29.8 FPS**, without an encoder timeout or rebuild. No game, library image
or user screenshot was saved for that test. This is a bounded device test, not a
guarantee of 60 FPS, zero latency or identical results on other hardware.

The source installer builds the adapter before registering the gaming template.
The configured project phone uses it now. Downloadable system images must be
rebuilt and checked against this source before claiming the same integration.

Project adaptation: José Miranda (Xcat2008), Portugal. Selkies, Pixelflux,
LinuxServer.io and the upstream graphics/media stacks retain their own authors
and licences.
