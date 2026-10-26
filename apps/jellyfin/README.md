# Jellyfin on the Redmi NAS

The CasaOS catalog template originally mounted Raspberry Pi/Broadcom video devices. The image downloaded correctly but Docker refused to start because `/dev/vcsm` was absent. A one-off edited installation was insufficient: uninstalling and reinstalling restored the catalog template. The permanent adaptation belongs in Homeio's compose materialization path, selected by `/etc/homeio/hardware-profile = redmi-ruby-nas`.

The patch only adapts the normal Jellyfin app and known Jellyfin images. It removes the optional GPU nodes and `/opt/vc/lib` mount; other applications, other devices and the NVIDIA variant are left intact. It adds no privileged mode. The patch and regression tests are under `homeio/`.

`compose.yaml` is a separate, standalone software-mode example. Set PUID/PGID to an existing media user/group and run `docker compose --env-file YOUR_ENV -f compose.yaml up -d`. Do not deploy it alongside a Homeio-managed Jellyfin using the same name/ports. Data is stored under `/DATA/AppData/jellyfin/config`, with media read-only at `/Media` inside the container.

Open `http://YOUR_PHONE_ADDRESS:8097` and complete Jellyfin's own first-run setup. Its account is separate from Homeio's. Start with hardware acceleration disabled; Mali desktop rendering does not establish MediaTek Jellyfin transcoding support. Prefer direct play for the first media test.

Upstream: https://jellyfin.org/ and https://docs.linuxserver.io/images/docker-jellyfin/ .
