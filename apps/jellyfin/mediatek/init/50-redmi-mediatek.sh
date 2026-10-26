#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-only
set -eu
marker=/config/.redmi-mediatek-initialized
test ! -e "$marker" || exit 0
file=/config/encoding.xml
if [ ! -s "$file" ]; then
 cat > "$file" <<'EOF'
<?xml version="1.0" encoding="utf-8"?>
<EncodingOptions xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <HardwareAccelerationType>v4l2m2m</HardwareAccelerationType>
  <EnableHardwareEncoding>true</EnableHardwareEncoding>
  <EncoderAppPathDisplay>/mediatek/ffmpeg</EncoderAppPathDisplay>
  <HardwareDecodingCodecs />
</EncodingOptions>
EOF
else
 grep -q '<EncodingOptions' "$file"
 cp "$file" /config/encoding.before-redmi-mediatek.xml
 for key in HardwareAccelerationType EnableHardwareEncoding EncoderAppPathDisplay; do
  case "$key" in
   HardwareAccelerationType) value=v4l2m2m ;;
   EnableHardwareEncoding) value=true ;;
   EncoderAppPathDisplay) value=/mediatek/ffmpeg ;;
  esac
  if grep -q "<$key>" "$file"; then
   sed -i "s#<$key>[^<]*</$key>#<$key>$value</$key>#g" "$file"
  else
   sed -i "s#</EncodingOptions>#<$key>$value</$key></EncodingOptions>#" "$file"
  fi
 done
fi
touch "$marker"
chown abc:abc "$file" "$marker"
echo 'Redmi MediaTek H.264 hardware encoding initialized.'
