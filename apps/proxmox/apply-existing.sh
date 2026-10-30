#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 José Miranda (Xcat2008)
# Maintenance only, inside an existing isolated Proxmox environment.
set -Eeuo pipefail
mode=${1:---check}
[[ $mode == --check || $mode == --apply ]] || {
    echo 'Usage: apply-existing.sh [--check|--apply]' >&2; exit 2;
}
bundle=$(cd "$(dirname "$0")" && pwd)
python3 "$bundle/preflight.py"
vendor=/usr/share/pve-edk2-firmware/AAVMF_CODE.fd.redmi-vendor
test -f "$vendor" || vendor=/usr/share/pve-edk2-firmware/AAVMF_CODE.fd
python3 - "$bundle/runtime" "$vendor" <<'PY'
import sys,platform,json,hashlib
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from firmware_compat import transform_vendor, SUPPORTED_VENDOR_SHA256
directory=Path(sys.argv[2]).parent
for name,expected in SUPPORTED_VENDOR_SHA256.items():
    target=directory/name
    vendor=directory/(name+'.redmi-vendor')
    if target.is_symlink() or vendor.is_symlink():raise SystemExit('Unexpected firmware symlink')
    data=(vendor if vendor.exists() else target).read_bytes()
    if platform.release().startswith('4.19.') and hashlib.sha256(data).hexdigest()!=expected:
        raise SystemExit('Unreviewed firmware: '+name)
    _,receipt=transform_vendor(data,platform.release())
    print(json.dumps(dict(receipt,variant=name,configuration_written=False)))
PY
if [[ $mode == --check ]]; then
    echo 'Existing-profile preflight passed. No configuration changed.'
    exit 0
fi
test "$EUID" = 0 || { echo 'Run the maintenance apply step as root inside Proxmox.' >&2; exit 1; }
python3 - <<'PY'
import json,subprocess
p=subprocess.run(['pvesh','get','/cluster/resources','--type','vm','--output-format','json'],capture_output=True,text=True,check=True)
if any(vm.get('status')=='running' for vm in json.loads(p.stdout)):
    raise SystemExit('Stop the VMs before applying the compatibility update.')
PY
stage=$(mktemp -d /tmp/redmi-proxmox-compat.XXXXXX)
trap 'rm -rf -- "$stage"' EXIT
cc -shared -fPIC -O2 -Wall -Wextra -Werror -pthread \
    -o "$stage/libredmi-kvm-cache-affinity.so" "$bundle/runtime/redmi-kvm-cache-affinity.c" -ldl
ensure_diversion() {
    local target=$1 backup="${1}.redmi-vendor" actual
    actual=$(dpkg-divert --truename "$target")
    if [[ $actual == "$target" ]]; then
        test ! -e "$backup" && test ! -L "$backup"
        dpkg-divert --local --rename --add --divert "$backup" "$target"
    else
        [[ $actual == "$backup" ]] || { echo "Unexpected existing diversion: $target" >&2; exit 1; }
        test -e "$backup"
    fi
}
install -d /usr/local/lib/redmi-proxmox /usr/local/sbin /var/lib/redmi-proxmox
install -m644 "$stage/libredmi-kvm-cache-affinity.so" /usr/local/lib/redmi-proxmox/
install -m644 "$bundle/runtime/redmi-kvm-cache-affinity.c" /usr/local/lib/redmi-proxmox/
install -m644 "$bundle/runtime/kvm-launcher.sh" /usr/local/lib/redmi-proxmox/
ensure_diversion /usr/bin/kvm
install -m755 "$bundle/runtime/refresh-cache-compat.py" /usr/local/sbin/redmi-pve-cache-compat-check
/usr/local/sbin/redmi-pve-cache-compat-check
ensure_diversion /usr/share/perl5/PVE/ProcFSTools.pm
ensure_diversion /usr/share/perl5/PVE/QemuServer/Drive.pm
install -m644 "$bundle/runtime/ProcFSTools.pm" /usr/share/perl5/PVE/ProcFSTools.pm
install -m644 "$bundle/runtime/Drive.pm" /usr/share/perl5/PVE/QemuServer/Drive.pm
ensure_diversion /usr/share/pve-edk2-firmware/AAVMF_CODE.fd
ensure_diversion /usr/share/pve-edk2-firmware/AAVMF_CODE.secboot.fd
install -m755 "$bundle/runtime/firmware_compat.py" /usr/local/sbin/redmi-pve-firmware-compat
/usr/local/sbin/redmi-pve-firmware-compat --apply
cat > /etc/apt/apt.conf.d/95-redmi-compatibility <<'EOF'
DPkg::Post-Invoke { "/usr/local/sbin/redmi-pve-firmware-compat --apply && /usr/local/sbin/redmi-pve-cache-compat-check && perl -MPVE::ProcFSTools -MPVE::QemuServer::Drive -e 1"; };
EOF
perl -MPVE::ProcFSTools -MPVE::QemuServer::Drive -e 'print "PVE compatibility modules loaded\n"'
/usr/bin/kvm --version
echo 'Compatibility sources installed. The NAS host, resource limits and network were not changed.'
echo 'Restart only the Proxmox environment from the NAS host before validation.'
