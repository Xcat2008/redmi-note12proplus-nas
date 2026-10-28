import { readFile, readdir } from "node:fs/promises";
import path from "node:path";

export type LinuxBatteryTelemetry = {
  hasBattery: true;
  isCharging: boolean;
  percent: number | null;
  timeRemaining: number;
  acConnected: boolean | null;
  manufacturer: string | null;
  cycleCount: number | null;
  designedCapacity: number | null;
  maxCapacity: number | null;
  capacityRatioPercent: number | null;
};

async function text(root: string, field: string): Promise<string | null> {
  try { return (await readFile(path.join(root, field), "utf8")).trim() || null; }
  catch { return null; }
}

function number(value: string | null): number | null {
  if (value === null || !/^-?\d+(\.\d+)?$/.test(value)) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function positive(value: number | null): number | null {
  return value !== null && value > 0 ? value : null;
}

async function supplies(root: string) {
  let names: string[];
  try { names = await readdir(root); } catch { return []; }
  return Promise.all(names.map(async (name) => {
    const directory = path.join(root, name);
    const keys = ["type", "present", "status", "capacity", "online", "cycle_count",
      "charge_full", "charge_full_design", "voltage_min_design", "energy_full",
      "energy_full_design", "manufacturer"] as const;
    const values = await Promise.all(keys.map((key) => text(directory, key)));
    return { name, ...Object.fromEntries(keys.map((key, index) => [key, values[index]])) } as
      { name: string } & Record<typeof keys[number], string | null>;
  }));
}

/** Read Linux power-supply attributes, including mobile battery/BMS layouts. */
export async function readLinuxBatteryTelemetry(
  root = "/sys/class/power_supply",
): Promise<LinuxBatteryTelemetry | null> {
  const devices = await supplies(root);
  const batteries = devices.filter((device) => device.type?.toLowerCase() === "battery");
  // An explicit absence on the pack must not be contradicted by its gauge.
  const pack = batteries.find((device) => device.name === "battery");
  if (pack?.present === "0") return null;
  const candidates = batteries.filter((device) => device.present !== "0");
  candidates.sort((a, b) =>
    Number(b.name === "battery") - Number(a.name === "battery") ||
    Number(b.present === "1") - Number(a.present === "1") || a.name.localeCompare(b.name));
  const battery = candidates[0];
  if (!battery) return null;
  const percent = number(battery.capacity);
  if (battery.present !== "1" && percent === null && positive(number(battery.charge_full)) === null) return null;

  const chargeFull = positive(number(battery.charge_full));
  const chargeDesign = positive(number(battery.charge_full_design));
  // The Redmi exposes one pack twice. The gauge has its real cycle count;
  // the generic pack node can return zero. Never merge unrelated batteries.
  const gauge = candidates.find((device) => device.name === "bms" && device !== battery &&
    chargeFull !== null && number(device.charge_full) === chargeFull &&
    number(device.capacity) === percent);
  const packCycles = number(battery.cycle_count);
  const gaugeCycles = gauge ? number(gauge.cycle_count) : null;
  const cycles = gaugeCycles !== null && gaugeCycles > 0 ? gaugeCycles : packCycles;
  const energyFull = positive(number(battery.energy_full));
  const energyDesign = positive(number(battery.energy_full_design));
  const designVoltage = positive(number(battery.voltage_min_design));
  // Instantaneous voltage is not a nominal capacity specification.
  const maxCapacity = energyFull !== null ? energyFull / 1_000_000 :
    chargeFull !== null && designVoltage !== null ? chargeFull * designVoltage / 1e12 : null;
  const designedCapacity = energyDesign !== null ? energyDesign / 1_000_000 :
    chargeDesign !== null && designVoltage !== null ? chargeDesign * designVoltage / 1e12 : null;
  const ratio = energyFull !== null && energyDesign !== null ? energyFull / energyDesign :
    chargeFull !== null && chargeDesign !== null ? chargeFull / chargeDesign : null;
  const status = battery.status?.toLowerCase();
  const charging = status === "charging";
  const onlineDevices = devices.filter((device) => ["0", "1"].includes(device.online ?? ""));
  // Internal charge-pump/converter nodes can stay online on battery power.
  // Prefer supplies explicitly labelled as external power by the kernel.
  const external = onlineDevices.filter((device) => /^(mains|wireless|ups|usb(?:_.*)?)$/i.test(device.type ?? ""));
  const power = external.length ? external : onlineDevices.filter((device) => /^(ac|usb|charger|dc)$/i.test(device.name));
  const acConnected = charging ? true : power.length ? power.some((device) => device.online === "1") : null;

  return {
    hasBattery: true, isCharging: charging,
    percent: percent !== null && percent >= 0 && percent <= 100 ? percent : null,
    timeRemaining: -1, acConnected,
    manufacturer: battery.manufacturer ?? gauge?.manufacturer ?? null,
    cycleCount: cycles !== null && Number.isInteger(cycles) && cycles >= 0 ? cycles : null,
    designedCapacity, maxCapacity,
    capacityRatioPercent: ratio !== null ? Number((ratio * 100).toFixed(1)) : null,
  };
}

/** CPU-labelled sensors only: a battery or charger is not a CPU temperature. */
export async function readLinuxCpuTemperature(root = "/sys/class/thermal") {
  let names: string[];
  try { names = await readdir(root); } catch { return null; }
  const readings = await Promise.all(names.filter((name) => /^thermal_zone\d+$/.test(name)).map(async (name) => {
    const directory = path.join(root, name);
    const type = (await text(directory, "type"))?.toLowerCase() ?? "";
    if (!/^(mtktscpu|cpu[-_]?therm(?:al)?|cpu\d+[-_]thermal|soc[-_]thermal|soc_max|x86_pkg_temp)$/.test(type)) return null;
    const raw = number(await text(directory, "temp"));
    if (raw === null || raw === 0) return null;
    const celsius = raw / 1000;
    return celsius > -20 && celsius <= 150 ? celsius : null;
  }));
  const valid = readings.filter((value): value is number => value !== null);
  if (!valid.length) return null;
  const main = Math.max(...valid);
  return { main, max: main, cores: [] as number[] };
}
