#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-or-later
set -eu
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
output=$(mktemp -d)
trap 'rm -rf -- "$output"' EXIT HUP INT TERM
sh "$here/../fetch-header.sh" "$output"
cc=${CC:-cc}
"$cc" -O2 -Wall -Wextra -Werror -shared -fPIC -I"$output" "$here/synthetic-async-core.c" -o "$output/synthetic-core.so"
"$cc" -O2 -Wall -Wextra -Werror -I"$output" "$here/test-pacing.c" -ldl -o "$output/test-pacing"
"$cc" -O2 -Wall -Wextra -Werror -I"$output" "$here/test-cpu-tier.c" -ldl -pthread -o "$output/test-cpu-tier"
"$output/test-pacing" "$output/synthetic-core.so"
"$output/test-cpu-tier" || { result=$?; [ "$result" -eq 77 ]; }
