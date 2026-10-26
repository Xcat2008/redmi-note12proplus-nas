#!/bin/sh
set -eu
# Demand-based clocks retain the firmware's frequency limits and thermal control.
if [ -x /usr/local/libexec/redmi-nas/mobile-power-saver ]; then
    profile=$(cat /var/lib/redmi-nas/energy-profile 2>/dev/null || printf balanced)
    case "$profile" in power-saver|balanced|performance) ;; *) profile=balanced ;; esac
    busctl --system call org.adishatz.Mps /org/adishatz/Mps org.freedesktop.DBus.Peer Ping
    busctl --system set-property org.freedesktop.UPower.PowerProfiles /org/freedesktop/UPower/PowerProfiles org.freedesktop.UPower.PowerProfiles ActiveProfile s "$profile"
    exit 0
fi
for policy in /sys/devices/system/cpu/cpufreq/policy*; do
    [ -d "$policy" ] || continue
    if grep -qw schedutil "$policy/scaling_available_governors"; then
        printf 'schedutil\n' > "$policy/scaling_governor"
    fi
done
