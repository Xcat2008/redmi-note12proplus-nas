import { execFile } from "node:child_process";
import { promisify } from "node:util";

const run = promisify(execFile);
export type MemoryExtensionStatus = {
  enabled: boolean; active: boolean; sizeBytes: number; usedBytes: number;
  reservedBytes: number; availableStorageBytes: number; zramTotalBytes: number;
  zramUsedBytes: number; availableMemoryBytes: number; kvmAvailable: boolean;
};
export class MemoryExtensionError extends Error {}
export async function memoryExtension(action: "status" | "enable" | "disable"): Promise<MemoryExtensionStatus> {
  let stdout = "";
  try {
    const result = await run("/usr/local/lib/redmi-nas/memory-extension.py", [action], { timeout: action === "status" ? 5000 : 240000, maxBuffer: 16384 });
    stdout = result.stdout;
  } catch (error) {
    stdout = String((error as { stdout?: string }).stdout ?? "");
    if (!stdout) throw new MemoryExtensionError("The memory service did not respond. Refresh to check its current state.");
  }
  const result = JSON.parse(stdout) as { data?: MemoryExtensionStatus; error?: string };
  if (!result.data || result.error) throw new MemoryExtensionError(result.error || "Memory status is unavailable.");
  return result.data;
}
