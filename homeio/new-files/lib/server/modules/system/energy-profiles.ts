import { readFile, readdir } from "node:fs/promises";
import dbus from "dbus-next";
import { readArmSocHardware } from "./arm-soc-hardware";
import { memoryExtension } from "./memory-extension";
import { batteryCharge } from "./battery-charge";

export const ENERGY_PROFILES = ["power-saver", "balanced", "performance"] as const;
export type EnergyProfile = typeof ENERGY_PROFILES[number];
const service = "org.freedesktop.UPower.PowerProfiles";
const objectPath = "/org/freedesktop/UPower/PowerProfiles";

export class EnergyProfileError extends Error {
  constructor(message: string, public status = 400) { super(message); }
}
export function validateEnergyProfile(value: unknown): EnergyProfile {
  if (typeof value !== "string" || !ENERGY_PROFILES.includes(value as EnergyProfile)) {
    throw new EnergyProfileError("Choose Power saver, Balanced or Performance.");
  }
  return value as EnergyProfile;
}
async function text(path: string) { try { return (await readFile(path, "utf8")).trim(); } catch { return ""; } }
function number(value: string) { const n = Number(value); return value !== "" && Number.isFinite(n) ? n : null; }

export function parseMemoryInfo(value: string) {
  const kib = (key: string) => Number(value.match(new RegExp(`^${key}:\\s+(\\d+)`, "m"))?.[1] ?? 0) * 1024;
  return { totalBytes: kib("MemTotal"), availableBytes: kib("MemAvailable"), swapTotalBytes: kib("SwapTotal"), swapFreeBytes: kib("SwapFree") };
}
export function parseGpuTelemetry(opp: string, state: string, usage: string) {
  const frequencies = [...opp.matchAll(/freq\s*=\s*(\d+)/g)].map(match => Number(match[1]));
  const current = state.match(/^idx:.*?freq:\s*(\d+)/m);
  const load = number(usage.split(/\s+/)[0] ?? "");
  return { currentMhz: current ? Number(current[1]) / 1000 : null,
    minMhz: frequencies.length ? Math.min(...frequencies) / 1000 : null,
    maxMhz: frequencies.length ? Math.max(...frequencies) / 1000 : null,
    utilizationPercent: load !== null && load >= 0 && load <= 100 ? load : null };
}

const holder = globalThis as typeof globalThis & { redmiNasEnergyBus?: dbus.MessageBus };
function bus() {
  if (!holder.redmiNasEnergyBus) {
    const connection = dbus.systemBus();
    holder.redmiNasEnergyBus = connection;
    connection.on("error", () => {
      if (holder.redmiNasEnergyBus === connection) { delete holder.redmiNasEnergyBus; connection.disconnect(); }
    });
  }
  return holder.redmiNasEnergyBus;
}
async function bounded<T>(promise: Promise<T>): Promise<T> {
  let timer: ReturnType<typeof setTimeout> | undefined;
  try { return await Promise.race([promise, new Promise<never>((_, reject) => {
    timer = setTimeout(() => reject(new EnergyProfileError("The energy service did not respond.", 504)), 10000);
    timer.unref?.();
  })]); } finally { clearTimeout(timer); }
}
async function nativeProfiles() {
  const object = await bounded(bus().getProxyObject(service, objectPath));
  const properties = object.getInterface("org.freedesktop.DBus.Properties");
  const [profile, version] = await bounded(Promise.all([
    properties.Get(service, "ActiveProfile"), properties.Get(service, "Version"),
  ]));
  return { properties, profile: String(profile.value), version: String(version.value) };
}
let hardware: ReturnType<typeof readArmSocHardware> | undefined;

export async function getEnergyStatus() {
  hardware ??= readArmSocHardware();
  const facts = await hardware;
  const [mem, opp, gpuState, gpuUsage, names, thermalNames] = await Promise.all([
    text("/proc/meminfo"), text("/proc/gpufreq/gpufreq_opp_dump"), text("/proc/gpufreq/gpufreq_var_dump"),
    text("/sys/kernel/ged/hal/gpu_utilization"), readdir("/sys/devices/system/cpu/cpufreq").catch(() => []),
    readdir("/sys/class/thermal").catch(() => []),
  ]);
  const clusters = await Promise.all(names.filter(name => /^policy\d+$/.test(name)).sort().map(async name => {
    const base = `/sys/devices/system/cpu/cpufreq/${name}`;
    const [cpus, governor, current, min, max] = await Promise.all([
      text(`${base}/related_cpus`), text(`${base}/scaling_governor`), text(`${base}/cpuinfo_cur_freq`),
      text(`${base}/cpuinfo_min_freq`), text(`${base}/cpuinfo_max_freq`),
    ]);
    return { name, cpus, governor, currentGhz: (number(current) ?? 0) / 1e6,
      minGhz: (number(min) ?? 0) / 1e6, maxGhz: (number(max) ?? 0) / 1e6 };
  }));
  const temperatures = await Promise.all(thermalNames.filter(name => /^thermal_zone\d+$/.test(name)).map(async name => {
    const base = `/sys/class/thermal/${name}`;
    return (await text(`${base}/type`)) === "mtktscpu" ? (number(await text(`${base}/temp`)) ?? 0) / 1000 : null;
  }));
  const cpuTemperature = temperatures.find(value => value !== null && value > 0 && value < 150) ?? null;
  let profile: { available: boolean; active: string | null; version: string | null; message?: string };
  try {
    const native = await nativeProfiles();
    profile = { available: native.version.includes("redmi-nas"), active: native.profile, version: native.version };
    if (!profile.available) profile.message = "Install the NAS energy adaptation before changing profiles.";
  } catch { profile = { available: false, active: null, version: null, message: "The native energy service is unavailable." }; }
  const expectedGovernor = profile.active === "balanced" ? "schedutil" : profile.active === "power-saver" ? "powersave" : "performance";
  return { profile, profiles: ENERGY_PROFILES, clusters, cpuTemperature,
    governorMatchesProfile: profile.available && clusters.length > 0 && clusters.every(cluster => cluster.governor === expectedGovernor),
    gpu: { model: facts.gpu?.model ?? "Integrated GPU", ...parseGpuTelemetry(opp, gpuState, gpuUsage), dvfs: "automatic" },
    memory: { ...parseMemoryInfo(mem), installedBytes: facts.installedMemoryBytes, dvfs: "automatic" },
    memoryExtension: await memoryExtension("status"),
    batteryCharge: await batteryCharge("status"),
  };
}

export async function setEnergyProfile(input: unknown) {
  const profile = validateEnergyProfile(input);
  const native = await nativeProfiles();
  if (!native.version.includes("redmi-nas")) throw new EnergyProfileError("The NAS energy adaptation is not installed.", 503);
  await bounded(native.properties.Set(service, "ActiveProfile", new dbus.Variant("s", profile)));
  const result = await getEnergyStatus();
  if (result.profile.active !== profile || !result.governorMatchesProfile)
    throw new EnergyProfileError("The selected profile was not applied to every CPU cluster.", 502);
  return result;
}
