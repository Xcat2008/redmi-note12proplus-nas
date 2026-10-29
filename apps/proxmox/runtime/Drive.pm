# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 José Miranda (Xcat2008)
package PVE::QemuServer::Drive;
use strict;
use warnings;
use POSIX ();
require '/usr/share/perl5/PVE/QemuServer/Drive.pm.redmi-vendor';
my $vendor_uring_default = \&PVE::QemuServer::Drive::storage_allows_io_uring_default;
{
    no warnings 'redefine';
    *storage_allows_io_uring_default = sub {
        my $release = (POSIX::uname())[2];
        # io_uring was added in Linux 5.1. Leave upstream choices untouched on
        # supported kernels; older phone kernels must use the normal fallback.
        if ($release =~ /^(\d+)\.(\d+)/ && ($1 < 5 || ($1 == 5 && $2 < 1))) {
            return;
        }
        return $vendor_uring_default->(@_);
    };
}
1;
