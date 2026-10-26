import { readFile, readdir } from "node:fs/promises";
import { join } from "node:path";

async function text(path: string): Promise<string | null> {
  try { return (await readFile(path, "utf8")).replace(/\0/g, "").trim(); }
  catch { return null; }
}

function cpuList(value: string): number[] {
  return [...new Set(value.split(/[\s,]+/).flatMap((part) => {
    if (!/^\d+(?:-\d+)?$/.test(part)) return [];
    const [first, last = first] = part.split("-").map(Number);
    return last >= first && last - first < 4096
      ? Array.from({ length: last - first + 1 }, (_, i) => first + i) : [];
  }))].sort((a, b) => a - b);
}

async function dirs(path: string): Promise<string[]> {
  try { return await readdir(path); } catch { return []; }
}

async function installedMemory(tree: string): Promise<number | null> {
  try {
    const addressCells = (await readFile(join(tree, "#address-cells"))).readUInt32BE();
    const sizeCells = (await readFile(join(tree, "#size-cells"))).readUInt32BE();
    if (![1, 2].includes(addressCells) || ![1, 2].includes(sizeCells)) return null;
    const stride = (addressCells + sizeCells) * 4;
    let total = 0;
    for (const name of await dirs(tree)) {
      if (!/^memory(?:@.*)?$/.test(name)) continue;
      const reg = await readFile(join(tree, name, "reg")).catch(() => null);
      if (!reg || reg.length % stride) continue;
      for (let offset = 0; offset < reg.length; offset += stride) {
        let bytes = 0;
        for (let cell = 0; cell < sizeCells; cell++) {
          bytes = bytes * 0x100000000 + reg.readUInt32BE(offset + (addressCells + cell) * 4);
        }
        total += bytes;
      }
    }
    return total > 0 && Number.isSafeInteger(total) ? total : null;
  } catch { return null; }
}

/** Read ARM cluster topology and integrated graphics that PCI/DMI probes miss. */
export async function readArmSocHardware(root = "/") {
  const sys = join(root, "sys/devices/system/cpu");
  const raw = await text(join(root, "proc/cpuinfo"));
  const parts = new Map<number, string>();
  for (const block of raw?.split(/\n\s*\n/) ?? []) {
    const id = block.match(/^processor\s*:\s*(\d+)/m);
    const part = block.match(/^CPU part\s*:\s*(0x[\da-f]+)/mi);
    if (id && part) parts.set(Number(id[1]), part[1].toLowerCase());
  }
  const online = await text(join(sys, "online"));
  const cpus = online ? cpuList(online) : [...parts.keys()];
  const names: Record<string, string> = { "0xd05": "Cortex-A55", "0xd41": "Cortex-A78" };
  const groups = new Map<string, number>();
  for (const id of cpus) {
    const part = parts.get(id);
    if (part) groups.set(names[part] ?? `ARM ${part}`, (groups.get(names[part] ?? `ARM ${part}`) ?? 0) + 1);
  }
  const siblings = await Promise.all(cpus.map(id => text(join(sys, `cpu${id}/topology/thread_siblings_list`))));
  const siblingKeys = siblings.map(value => value ? cpuList(value).join(",") : null);
  const policies = await Promise.all((await dirs(join(sys, "cpufreq")))
    .filter(name => /^policy\d+$/.test(name)).map(async name => {
      const path = join(sys, "cpufreq", name);
      const [related, max, current, governor] = await Promise.all([
        text(join(path, "related_cpus")), text(join(path, "cpuinfo_max_freq")),
        text(join(path, "scaling_cur_freq")), text(join(path, "scaling_governor")),
      ]);
      const count = cpuList(related ?? "").filter(id => cpus.includes(id)).length;
      return { count, max: Number(max) || 0, current: Number(current) || 0, governor };
    }));
  const maxKhz = Math.max(0, ...policies.map(p => p.max));
  const currentCount = policies.filter(p => p.current > 0).reduce((sum, p) => sum + p.count, 0);
  const governors = [...new Set(policies.flatMap(p => p.governor ? [p.governor] : []))];
  const cpu = cpus.length && groups.size ? {
    brand: [...groups].map(([name, count]) => `${count}× ${name}`).join(" + "),
    cores: cpus.length,
    // Thread masks are globally unique; core_id is reused across ARM clusters.
    physicalCores: siblingKeys.every(Boolean) ? new Set(siblingKeys).size : null,
    maxSpeedGhz: maxKhz > 0 ? maxKhz / 1_000_000 : null,
    speedGhz: currentCount ? Number((policies.reduce((sum, p) => sum + p.current * p.count, 0) / currentCount / 1_000_000).toFixed(2)) : null,
    governor: governors.length ? governors.join(" / ") : null,
  } : null;

  let gpu: { vendor: string; model: string; bus: string; vramBytes: null; subVendor: null; sharedMemory: true } | null = null;
  const platform = join(root, "sys/devices/platform");
  for (const name of await dirs(platform)) {
    if (!name.toLowerCase().includes("mali")) continue;
    const info = await text(join(platform, name, "gpuinfo"));
    const match = info?.match(/(Mali-[\w-]+)\s+(\d+)\s+cores/i);
    if (match) {
      gpu = { vendor: "ARM", model: `${match[1]} MC${match[2]}`, bus: "Integrated", vramBytes: null, subVendor: null, sharedMemory: true };
      break;
    }
  }
  return { cpu, gpu, installedMemoryBytes: await installedMemory(join(root, "sys/firmware/devicetree/base")) };
}
