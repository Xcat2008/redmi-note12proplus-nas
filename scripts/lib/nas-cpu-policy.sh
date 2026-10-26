#!/bin/sh
set -eu
# Demand-based clocks retain the firmware's frequency limits and thermal control.
for policy in /sys/devices/system/cpu/cpufreq/policy*; do
    [ -d "$policy" ] || continue
    if grep -qw schedutil "$policy/scaling_available_governors"; then
        printf 'schedutil\n' > "$policy/scaling_governor"
    fi
done
