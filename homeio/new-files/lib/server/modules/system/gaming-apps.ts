import { execFile } from "node:child_process";
import { promisify } from "node:util";
const run = promisify(execFile);
export type SteamAppStatus = { installed: boolean; running: boolean; startupEnabled: boolean; focused?: boolean; retroarchInstalled: boolean; retroarchRunning: boolean };
export class GamingAppError extends Error {}
export async function controlGamingApp(action: "status" | "steam-start" | "steam-stop" | "retroarch-focus" | "retroarch-stop"): Promise<SteamAppStatus> {
  let stdout = "";
  try { stdout = (await run("/usr/local/lib/redmi-nas/steam/gaming-app-control.py", [action], { timeout: action === "status" ? 5000 : 65000, maxBuffer: 16384 })).stdout; }
  catch (error) {
    stdout = String((error as { stdout?: string }).stdout ?? "");
    if (!stdout) throw new GamingAppError("The application did not respond. Refresh its status before trying again.");
  }
  const result = JSON.parse(stdout) as { data?: SteamAppStatus; error?: string };
  if (!result.data || result.error) throw new GamingAppError(result.error || "Application status is unavailable.");
  return result.data;
}
