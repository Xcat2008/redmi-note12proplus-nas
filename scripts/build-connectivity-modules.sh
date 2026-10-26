#!/bin/bash
set -euo pipefail
task=$(realpath "${1:?Usage: build-connectivity-modules.sh BUILD_ROOT}")
test -s "$task/mtk-modules/connectivity/conninfra/Module.symvers" || { echo "Build ruby conninfra against this kernel output first." >&2; exit 1; }
export PATH="$task/toolchains/clang-r383902/bin:$PATH"
export LD_LIBRARY_PATH="$task/toolchains/clang-r383902/lib64"
export TARGET_BUILD_VARIANT=user
mkdir -p "$task/vendor/mediatek"
if [ ! -e "$task/vendor/mediatek/kernel_modules" ]; then
    ln -s "$task/mtk-modules" "$task/vendor/mediatek/kernel_modules"
fi
[ "$(readlink -f "$task/vendor/mediatek/kernel_modules")" = "$task/mtk-modules" ]
if [ ! -e "$task/mtk-modules/connectivity/wlan/core/gen4m" ]; then
    ln -s "$task/wlan-pissarro/connectivity/wlan/core/gen4m" "$task/mtk-modules/connectivity/wlan/core/gen4m"
fi
base=(make -C "$task/kernel" "O=$task/linux-output" "KERNEL_OUT=$task/linux-output"
      ARCH=arm64 LLVM=1 LLVM_IAS=1 CROSS_COMPILE=aarch64-linux-gnu-
      CROSS_COMPILE_COMPAT=arm-linux-gnueabi- CLANG_TRIPLE=aarch64-linux-gnu-
      CC=clang LD=ld.lld AR=llvm-ar NM=llvm-nm OBJCOPY=llvm-objcopy
      OBJDUMP=llvm-objdump READELF=llvm-readelf STRIP=llvm-strip HOSTCC=gcc HOSTCXX=g++)
"${base[@]}" "M=$task/mtk-modules/connectivity/connfem" -j6 modules
"${base[@]}" "M=$task/wlan-pissarro/connectivity/wlan/adaptor" \
    "KBUILD_EXTRA_SYMBOLS=$task/mtk-modules/connectivity/conninfra/Module.symvers" \
    ADAPTOR_OPTS=CONNAC2X2_SOC5_0 MODULE_NAME=wmt_chrdev_wifi -j6 modules
"${base[@]}" "M=$task/mtk-modules/connectivity/wlan/core/gen4m" \
    "KBUILD_EXTRA_SYMBOLS=$task/mtk-modules/connectivity/conninfra/Module.symvers $task/wlan-pissarro/connectivity/wlan/adaptor/Module.symvers $task/mtk-modules/connectivity/connfem/Module.symvers" \
    CONFIG_MTK_COMBO_WIFI_HIF=axi MODULE_NAME=wlan_drv_gen4m MTK_COMBO_CHIP=SOC5_0 \
    WLAN_CHIP_ID=6877 MTK_ANDROID_WMT=y MTK_ANDROID_EMI=y -j6 modules
echo connectivity_modules_compiled
