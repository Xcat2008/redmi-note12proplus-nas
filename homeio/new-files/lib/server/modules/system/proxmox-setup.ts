import { execFile } from "node:child_process";
export type ProxmoxSetupStatus = {
  configured: boolean; ready: boolean; errors: string[]; busy: boolean;
  job: { state: string; error?: string }; webPort: number;
};
export async function proxmoxSetup(action: "status" | "enable", password?: string): Promise<ProxmoxSetupStatus> {
  return new Promise((resolve, reject) => {
    const child = execFile("/usr/local/sbin/redmi-proxmox-control", [action],
      { timeout: 15000, maxBuffer: 16384 }, (error, stdout) => {
        try {
          const result = JSON.parse(stdout) as { data?: ProxmoxSetupStatus; error?: string };
          if (error || !result.data || result.error) return reject(new Error(result.error || "Proxmox setup is unavailable."));
          resolve(result.data);
        } catch { reject(new Error("Proxmox setup did not return a valid status.")); }
      });
    child.stdin?.end(action === "enable" ? JSON.stringify({ password }) : undefined);
  });
}
