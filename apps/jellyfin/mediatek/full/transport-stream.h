// SPDX-License-Identifier: AGPL-3.0-only
#pragma once
#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <vector>
// Single H.264 program, with the codec's real presentation timestamps.
class TransportStream {
  FILE *out;
  uint8_t videoCC = 0, patCC = 0, pmtCC = 0;
  bool tables = false;
  static uint32_t crc(const std::vector<uint8_t> &b) {
    uint32_t c = 0xffffffff;
    for (auto x : b) {
      c ^= uint32_t(x) << 24;
      for (int n = 0; n < 8; n++)
        c = (c << 1) ^ ((c & 0x80000000) ? 0x04c11db7 : 0);
    }
    return c;
  }
  bool section(uint16_t pid, uint8_t &cc, std::vector<uint8_t> b) {
    uint32_t c = crc(b);
    for (int i = 3; i >= 0; i--)
      b.push_back(c >> (8 * i));
    uint8_t p[188];
    std::fill(p, p + 188, 0xff);
    p[0] = 0x47;
    p[1] = 0x40 | (pid >> 8);
    p[2] = pid;
    p[3] = 0x10 | (cc++ & 15);
    p[4] = 0;
    std::copy(b.begin(), b.end(), p + 5);
    return fwrite(p, 1, 188, out) == 188;
  }
  bool headers() {
    return section(0, patCC,
                   {0x00, 0xb0, 0x0d, 0, 1, 0xc1, 0, 0, 0, 1, 0xf0, 0}) &&
           section(0x1000, pmtCC,
                   {0x02, 0xb0, 0x12, 0, 1, 0xc1, 0, 0, 0xe1, 0, 0xf0, 0, 0x1b,
                    0xe1, 0, 0xf0, 0});
  }

public:
  explicit TransportStream(FILE *f) : out(f) {}
  bool frame(const uint8_t *data, size_t size, int64_t timeUs, bool key,
             const std::vector<uint8_t> &config) {
    if (!tables || key) {
      if (!headers())
        return false;
      tables = true;
    }
    uint64_t pts = uint64_t(std::max<int64_t>(0, timeUs)) * 90 / 1000;
    std::vector<uint8_t> b = {0,
                              0,
                              1,
                              0xe0,
                              0,
                              0,
                              0x80,
                              0x80,
                              5,
                              uint8_t(0x21 | ((pts >> 29) & 0x0e)),
                              uint8_t(pts >> 22),
                              uint8_t(((pts >> 14) & 0xfe) | 1),
                              uint8_t(pts >> 7),
                              uint8_t(((pts << 1) & 0xfe) | 1),
                              0,
                              0,
                              0,
                              1,
                              9,
                              0xf0};
    if (key)
      b.insert(b.end(), config.begin(), config.end());
    b.insert(b.end(), data, data + size);
    size_t offset = 0;
    bool first = true;
    while (offset < b.size()) {
      uint8_t p[188];
      std::fill(p, p + 188, 0xff);
      p[0] = 0x47;
      p[1] = 1 | (first ? 0x40 : 0);
      p[2] = 0;
      size_t count = std::min<size_t>(first ? 176 : 184, b.size() - offset);
      bool adaptation = first || count < 184;
      p[3] = (adaptation ? 0x30 : 0x10) | (videoCC++ & 15);
      size_t pos = 4;
      if (adaptation) {
        size_t len = 183 - count;
        p[pos++] = len;
        if (len) {
          p[pos++] = first ? (0x10 | (key ? 0x40 : 0)) : 0;
          if (first) {
            p[pos++] = pts >> 25;
            p[pos++] = pts >> 17;
            p[pos++] = pts >> 9;
            p[pos++] = pts >> 1;
            p[pos++] = ((pts & 1) << 7) | 0x7e;
            p[pos++] = 0;
          }
          pos = 5 + len;
        }
      }
      std::copy(b.begin() + offset, b.begin() + offset + count, p + pos);
      if (fwrite(p, 1, 188, out) != 188)
        return false;
      offset += count;
      first = false;
    }
    return fflush(out) == 0;
  }
};
