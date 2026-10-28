#!/bin/bash
set -euo pipefail
base=/opt/redmi-native-build
export PATH=$HOME/.cargo/bin:$base/native-driver-tools/bin:$PATH
# System compiler prerequisites are installed separately through the WSL root entry point.
python3 -m venv "$base/native-driver-tools"
"$base/native-driver-tools/bin/pip" install 'meson>=1.7,<2' mako PyYAML packaging >"$base/native-driver-python-tools.log" 2>&1
rustup target add aarch64-unknown-linux-gnu
CARGO_BUILD_JOBS=6 cargo install bindgen-cli --version 0.71.1 --locked >"$base/native-driver-bindgen-build.log" 2>&1
cd "$base/malisx2-trial-source"
git fetch --depth 1 origin tag v0.2.3
git checkout --detach v0.2.3
mkdir -p mesa
git -C mesa init
git -C mesa fetch --depth 1 https://github.com/bmdhacks/armsx2-turnip.git 2b9a7e936fd40969c650c26ed10f1a4078b8f246
git -C mesa checkout --detach FETCH_HEAD
printf 'Native-driver compiler tools and pinned source ready\n'
