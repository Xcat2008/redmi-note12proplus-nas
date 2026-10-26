import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, mkdir, writeFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { readArmSocHardware } from "./arm-soc-hardware";

async function fixture() {
  const root = await mkdtemp(join(tmpdir(), "nas-arm-hardware-"));
  const put = async (path: string, value: string | Buffer) => {
    const target = join(root, path);
    await mkdir(dirname(target), { recursive: true });
    await writeFile(target, value);
  };
  return { root, put, close: () => rm(root, { recursive: true, force: true }) };
}

function cells(values: number[]) {
  const buffer = Buffer.alloc(values.length * 4);
  values.forEach((value, index) => buffer.writeUInt32BE(value, index * 4));
  return buffer;
}

test("heterogeneous ARM: count all8cores and take2.6GHz from the performance cluster", async () => {
  const f = await fixture();
  try {
    await f.put("proc/cpuinfo", Array.from({ length: 8 }, (_, i) =>
      `processor : ${i}\nCPU part : ${i < 6 ? "0xd05" : "0xd41"}\n`).join("\n"));
    await f.put("sys/devices/system/cpu/online", "0-7");
    for (let i = 0; i < 8; i++) {
      await f.put(`sys/devices/system/cpu/cpu${i}/topology/thread_siblings_list`, String(i));
      // This kernel reuses core_id0and1 across clusters; those are not global IDs.
      await f.put(`sys/devices/system/cpu/cpu${i}/topology/core_id`, String(i < 6 ? i : i - 6));
    }
    for (const [id, cpus, max, current] of [[0, "0 1 2 3 4 5", 2_000_000, 500_000], [6, "6 7", 2_600_000, 650_000]] as const) {
      const base = `sys/devices/system/cpu/cpufreq/policy${id}`;
      await f.put(`${base}/related_cpus`, cpus);
      await f.put(`${base}/cpuinfo_max_freq`, String(max));
      await f.put(`${base}/scaling_cur_freq`, String(current));
      await f.put(`${base}/scaling_governor`, "schedutil");
    }
    const result = await readArmSocHardware(f.root);
    assert.equal(result.cpu?.cores, 8);
    assert.equal(result.cpu?.physicalCores, 8);
    assert.equal(result.cpu?.brand, "6× Cortex-A55 + 2× Cortex-A78");
    assert.equal(result.cpu?.maxSpeedGhz, 2.6);
    assert.equal(result.cpu?.speedGhz, 0.54);
    assert.equal(result.cpu?.governor, "schedutil");
  } finally { await f.close(); }
});

test("device tree reports physical8GiB and multiple banks without substituting usable memory", async () => {
  const f = await fixture();
  try {
    const tree = "sys/firmware/devicetree/base";
    await f.put(`${tree}/#address-cells`, cells([2]));
    await f.put(`${tree}/#size-cells`, cells([2]));
    await f.put(`${tree}/memory/reg`, cells([0, 0x40000000, 2, 0]));
    assert.equal((await readArmSocHardware(f.root)).installedMemoryBytes, 8 * 1024 ** 3);
    await f.put(`${tree}/memory/reg`, cells([0, 0x40000000, 1, 0, 1, 0x40000000, 1, 0]));
    assert.equal((await readArmSocHardware(f.root)).installedMemoryBytes, 8 * 1024 ** 3);
    await f.put(`${tree}/memory/reg`, Buffer.from([1, 2, 3]));
    assert.equal((await readArmSocHardware(f.root)).installedMemoryBytes, null);
  } finally { await f.close(); }
});

test("Mali platform GPU uses shared memory and does not invent dedicated VRAM", async () => {
  const f = await fixture();
  try {
    await f.put("sys/devices/platform/13000000.mali/gpuinfo", "Mali-G68 4 cores r1p1 0x9204\n");
    const { gpu } = await readArmSocHardware(f.root);
    assert.equal(gpu?.model, "Mali-G68 MC4");
    assert.equal(gpu?.vendor, "ARM");
    assert.equal(gpu?.sharedMemory, true);
    assert.equal(gpu?.vramBytes, null);
  } finally { await f.close(); }
});

test("missing or unsupported probes return no inferred CPU, GPU or installed RAM", async () => {
  const f = await fixture();
  try {
    const result = await readArmSocHardware(f.root);
    assert.equal(result.cpu, null);
    assert.equal(result.gpu, null);
    assert.equal(result.installedMemoryBytes, null);
  } finally { await f.close(); }
});
