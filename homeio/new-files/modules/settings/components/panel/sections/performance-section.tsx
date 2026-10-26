"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import type { SVGProps } from "react";
import type { getEnergyStatus } from "@/lib/server/modules/system/energy-profiles";
import { SETTINGS_PANEL_INSET } from "@/modules/settings/components/panel/surface";
import { cn } from "@/lib/utils";

type Status = Awaited<ReturnType<typeof getEnergyStatus>>;
const choices = [
  { id: "power-saver", title: "Power saver", description: "Requests minimum CPU clocks. Lower performance for lighter tasks." },
  { id: "balanced", title: "Balanced", description: "Recommended. CPU clocks rise with demand and fall when work is finished." },
  { id: "performance", title: "Performance", description: "Requests maximum factory CPU clocks. Uses more power and produces more heat." },
] as const;
const gib = (bytes: number | null) => bytes === null ? "—" : `${(bytes / 1024 ** 3).toFixed(1)} GiB`;

export function PerformanceIcon(props: SVGProps<SVGSVGElement>) {
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" aria-hidden="true" {...props}>
    <path d="M4 18a9 9 0 1 1 16 0M12 13l5-5M7 18h10" /><circle cx="12" cy="13" r="1" />
  </svg>;
}
export function PerformanceSection() {
  const [data, setData] = useState<Status | null>(null);
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const mounted = useRef(true);
  const generation = useRef(0);
  const refresh = useCallback(async () => {
    const version = generation.current;
    try {
      const response = await fetch("/api/v1/performance", { cache: "no-store" });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || "Performance status is unavailable.");
      if (mounted.current && version === generation.current) setData(result.data);
    } catch (cause) { if (mounted.current) setError(cause instanceof Error ? cause.message : "Performance status is unavailable."); }
  }, []);
  useEffect(() => {
    mounted.current = true; void refresh();
    const timer = setInterval(() => { if (!document.hidden) void refresh(); }, 3000);
    return () => { mounted.current = false; clearInterval(timer); };
  }, [refresh]);
  async function select(profile: string) {
    generation.current++; setPending(true); setError("");
    try {
      const response = await fetch("/api/v1/performance", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ profile }) });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || "The profile could not be applied.");
      if (mounted.current) setData(result.data);
    } catch (cause) { if (mounted.current) setError(cause instanceof Error ? cause.message : "The profile could not be applied."); }
    finally { generation.current++; if (mounted.current) setPending(false); }
  }
  return <div className="space-y-4" data-testid="nas-performance-panel">
    <p className="text-xs leading-relaxed text-muted-foreground">Choose how the CPU responds to work. The NAS stays available with the display off. Your choice is saved across restarts.</p>
    {error && <p role="alert" className="rounded-lg border border-status-red/30 p-3 text-xs">{error}</p>}
    {!data && <p className="text-sm text-muted-foreground">Reading hardware status…</p>}
    {data && <>
      {!data.profile.available && <p role="status" className="text-xs text-muted-foreground">{data.profile.message}</p>}
      <div role="radiogroup" aria-label="Energy profile" className="grid gap-2">
        {choices.map(choice => <button key={choice.id} role="radio" aria-checked={data.profile.active === choice.id}
          disabled={pending || !data.profile.available} onClick={() => void select(choice.id)}
          className={cn(SETTINGS_PANEL_INSET, "p-3 text-left disabled:cursor-wait disabled:opacity-50", data.profile.active === choice.id && "border-primary/60 bg-primary/10")}>
          <span className="text-sm font-medium">{choice.title}{data.profile.active === choice.id ? " · Active" : ""}</span>
          <span className="mt-1 block text-xs leading-relaxed text-muted-foreground">{choice.description}</span>
        </button>)}
      </div>
      {data.profile.available && !data.governorMatchesProfile && <p role="alert" className="text-xs text-status-red">The CPU governors do not match the selected profile. Apply the profile again.</p>}
      <div className={cn(SETTINGS_PANEL_INSET, "space-y-3 p-4")}>
        <h3 className="text-sm font-medium">CPU clusters</h3>
        {data.clusters.map(cluster => <div key={cluster.name} className="flex flex-wrap justify-between gap-2 border-t border-glass-border/50 pt-2 text-xs">
          <div><p className="font-medium">CPUs {cluster.cpus}</p><p className="mt-1 text-muted-foreground">{cluster.governor} · {cluster.minGhz.toFixed(2)}–{cluster.maxGhz.toFixed(2)} GHz</p></div>
          <span className="font-mono">{cluster.currentGhz.toFixed(2)} GHz reported</span>
        </div>)}
        <p className="text-xs text-muted-foreground">CPU temperature: {data.cpuTemperature === null ? "—" : `${data.cpuTemperature.toFixed(1)} °C`}. Thermal and battery protection remain active.</p>
      </div>
      <div className={cn(SETTINGS_PANEL_INSET, "space-y-2 p-4 text-xs")}>
        <h3 className="text-sm font-medium">GPU and memory</h3>
        <p>{data.gpu.model}: {data.gpu.currentMhz ?? "—"} MHz · {data.gpu.utilizationPercent ?? "—"}% load</p>
        <p className="text-muted-foreground">GPU factory range: {data.gpu.minMhz ?? "—"}–{data.gpu.maxMhz ?? "—"} MHz. MediaTek GPU and memory DVFS remain automatic in all CPU profiles.</p>
        <p>RAM: {gib(data.memory.installedBytes)} physical · {gib(data.memory.totalBytes)} available to Linux · {gib(data.memory.availableBytes)} currently available</p>
        <p className="text-muted-foreground">A clock reading can show the last active frequency while a core is idle. It does not measure power consumption.</p>
      </div>
      <div className={cn(SETTINGS_PANEL_INSET, "p-4")}>
        <div className="flex items-center justify-between gap-3"><h3 className="text-sm font-medium">Overclock</h3><button disabled className="rounded-lg border border-glass-border px-3 py-1 text-xs opacity-50">Not validated</button></div>
        <p className="mt-2 text-xs leading-relaxed text-muted-foreground">{data.overclock.reason}</p>
      </div>
    </>}
  </div>;
}
