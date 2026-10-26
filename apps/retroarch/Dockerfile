# SPDX-License-Identifier: AGPL-3.0-only
FROM lscr.io/linuxserver/retroarch@sha256:f148c679b390305b598b2175d9ec7654700ac148ba5773a363b84c5c792ae5e5
ARG SUNSHINE_URL=https://github.com/LizardByte/Sunshine/releases/download/v2026.914.233613/sunshine_2026.914.233613-1%2Bubuntu26.04_arm64.deb
ARG SUNSHINE_SHA256=174fa9123362c93eac164554a0651ecab17d64d9525fccd9974964fceec553af
RUN curl -fL --retry 3 "$SUNSHINE_URL" -o /tmp/sunshine.deb \
 && echo "$SUNSHINE_SHA256  /tmp/sunshine.deb" | sha256sum -c - \
 && apt-get update \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends /tmp/sunshine.deb \
 && setcap -r /usr/bin/sunshine \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/* /tmp/sunshine.deb
