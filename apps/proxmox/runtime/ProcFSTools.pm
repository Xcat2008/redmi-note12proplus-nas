# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 José Miranda (Xcat2008)
package PVE::ProcFSTools;
use strict;
use warnings;
require '/usr/share/perl5/PVE/ProcFSTools.pm.redmi-vendor';
my $vendor_cpuinfo = \&PVE::ProcFSTools::read_cpuinfo;
my $vendor_parse_pressure = \&PVE::ProcFSTools::parse_pressure;
{
    no warnings 'redefine';
    *parse_pressure = sub {
        my ($path) = @_;
        my $stats = $vendor_parse_pressure->(@_);
        # Linux before 5.13 has CPU 'some' PSI but no 'full' counter.
        # Match PVE's unavailable-PSI fallback, without masking real values.
        if (defined($stats) && $path =~ m{/cpu\.pressure$} && !exists($stats->{full})
            && $^O eq 'linux' && do { open(my $f, '<', '/proc/sys/kernel/osrelease'); my $r = <$f>; close($f); $r =~ /^4\./ }) {
            $stats->{full} = { avg10 => 0, avg60 => 0, avg300 => 0, total => 0 };
        }
        return $stats;
    };
    *read_cpuinfo = sub {
        my $info = { %{$vendor_cpuinfo->(@_)} };
        # LXCFS supplies the actual cgroup CPU budget; the original parser
        # otherwise labels every ARM core using the first physical CPU part.
        my $midr;
        if (open(my $fh, '<', '/sys/devices/system/cpu/cpu6/regs/identification/midr_el1')) {
            $midr = <$fh>; close($fh); chomp($midr) if defined($midr);
        }
        if (defined($midr) && ((hex($midr) >> 4) & 0xfff) == 0xd41) {
            $info->{model} = 'Cortex-A78 (MediaTek Dimensity 1080)';
            $info->{vendor} = 'ARM';
            if (open(my $fh, '<', '/proc/self/status')) {
                while (my $line = <$fh>) {
                    next if $line !~ /^Cpus_allowed_list:\s*([0-9,-]+)/;
                    my $count = 0;
                    for my $range (split /,/, $1) {
                        if ($range =~ /^(\d+)-(\d+)$/) { $count += $2 - $1 + 1; }
                        elsif ($range =~ /^\d+$/) { $count++; }
                    }
                    $info->{cpus} = $count if $count > 0;
                }
                close($fh);
            }
            $info->{cores} = $info->{cpus};
            $info->{sockets} = 1;
            if ($info->{cpus} == 8) {
                $info->{model} = 'MediaTek Dimensity 1080 (6 Cortex-A55 + 2 Cortex-A78)';
            }
            if (open(my $fh, '<', '/sys/devices/system/cpu/cpu6/cpufreq/scaling_cur_freq')) {
                my $khz = <$fh>; close($fh);
                $info->{mhz} = int($khz / 1000) if defined($khz) && $khz =~ /^\d+/;
            }
        }
        return $info;
    };
}
1;
