#!/bin/bash
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 José Miranda (Xcat2008)
# The diverted vendor executable is updated by dpkg. Keep its normal argv[0].
set -eu
if [[ $(uname -m) == aarch64 && $(uname -r) == 4.19.* ]]; then
    compat=/usr/local/lib/redmi-proxmox/libredmi-kvm-cache-affinity.so
    test -r "$compat"
    export LD_PRELOAD="$compat${LD_PRELOAD:+:$LD_PRELOAD}"
fi
exec -a /usr/bin/kvm /usr/bin/kvm.redmi-vendor "$@"
