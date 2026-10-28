import { execFile } from "node:child_process";
import { promisify } from "node:util";
const run = promisify(execFile);
export type BatteryChargeStatus = {
  supported: boolean; enabled: boolean; active: boolean;
  lowerPercent: number; upperPercent: number; capacityPercent: number | null;
  temperatureC: number | null; chargingStatus: string | null; powerPathEnabled: boolean;
};
export class BatteryChargeError extends Error {}
export async function batteryCharge(action: "status" | "enable" | "disable"): Promise<BatteryChargeStatus> {
  let stdout = "";
  try { stdout = (await run("/usr/local/lib/redmi-nas/battery-charge.py", [action], { timeout: 25000, maxBuffer: 16384 })).stdout; }
  catch (error) {
    stdout = String((error as { stdout?: string }).stdout ?? "");
    if (!stdout) throw new BatteryChargeError("The battery service did not respond. Refresh to check its current state.");
  }
  const result = JSON.parse(stdout) as { data?: BatteryChargeStatus; error?: string };
  if (!result.data || result.error) throw new BatteryChargeError(result.error || "Battery status is unavailable.");
  return result.data;
}
