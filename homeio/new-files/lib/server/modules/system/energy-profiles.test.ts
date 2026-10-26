import assert from "node:assert/strict";
import test from "node:test";
import { parseGpuTelemetry, parseMemoryInfo, validateEnergyProfile } from "./energy-profiles";

test("only native factory-limit profiles can be selected", () => {
  for (const value of ["power-saver", "balanced", "performance"]) assert.equal(validateEnergyProfile(value), value);
  for (const value of [null, 1, {}, "unsupported", "performance;reboot"]) assert.throws(() => validateEnergyProfile(value));
});
test("memory availability uses the kernel's available count", () => {
  const info = parseMemoryInfo("MemTotal: 8192 kB\nMemFree: 128 kB\nMemAvailable: 4096 kB\nSwapTotal: 2048 kB\nSwapFree: 1024 kB\n");
  assert.equal(info.availableBytes, 4096 * 1024); assert.equal(info.totalBytes, 8192 * 1024);
  assert.equal(info.swapFreeBytes, 1024 * 1024);
});
test("Mali telemetry handles reported frequency and missing nodes", () => {
  const gpu = parseGpuTelemetry("[00] freq = 950000, vgpu = 69000\n[01] freq = 385000, vgpu = 55000", "idx: 1, freq: 385000, vgpu: 55000", "96 0 4");
  assert.deepEqual(gpu, { currentMhz: 385, minMhz: 385, maxMhz: 950, utilizationPercent: 96 });
  assert.equal(parseGpuTelemetry("", "", "").currentMhz, null);
});
