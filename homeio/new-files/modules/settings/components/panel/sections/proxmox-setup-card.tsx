"use client";
import { useEffect, useState } from "react";
import type { ProxmoxSetupStatus } from "@/lib/server/modules/system/proxmox-setup";
import { SETTINGS_PANEL_INSET } from "@/modules/settings/components/panel/surface";
import { cn } from "@/lib/utils";

export function ProxmoxSetupCard() {
  const [data, setData] = useState<ProxmoxSetupStatus | null>(null);
  const [error, setError] = useState("");
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [pending, setPending] = useState(false);
  const [href, setHref] = useState("");
  useEffect(() => {
    let alive = true;
    const url = new URL(window.location.href); url.protocol = "https:"; url.port = "8006"; url.pathname = "/"; url.search = ""; url.hash = ""; setHref(url.href);
    async function refresh() {
      try {
        const response = await fetch("/api/v1/proxmox", { cache: "no-store" });
        const result = await response.json();
        if (!response.ok) throw new Error(result.error || "Could not read Proxmox status.");
        if (alive) setData(result.data);
      } catch (cause) { if (alive) setError(cause instanceof Error ? cause.message : "Could not read Proxmox status."); }
    }
    void refresh(); const timer = setInterval(() => { if (!document.hidden) void refresh(); }, 5000);
    return () => { alive = false; clearInterval(timer); };
  }, []);
  async function enable(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError("");
    if (password.length < 8 || password !== confirmation) { setError("Use at least 8 characters and enter the same password twice."); return; }
    setPending(true);
    try {
      const response = await fetch("/api/v1/proxmox", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ password }) });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || "Could not start Proxmox setup.");
      setData(result.data); setPassword(""); setConfirmation("");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Could not start Proxmox setup."); }
    finally { setPending(false); }
  }
  return <section className={cn(SETTINGS_PANEL_INSET, "space-y-3 p-4 text-xs")} aria-label="Virtual machines">
    <h3 className="text-sm font-medium">Virtual machines · Proxmox</h3>
    <p className="text-muted-foreground">Optional experimental ARM64 environment. Off by default. Shares the phone's RAM and CPUs with the NAS.</p>
    {error && <p role="alert">{error}</p>}
    {!data && <p role="status">Checking optional setup…</p>}
    {data?.configured && <><p>Configured. Sign in as <strong>root</strong>, realm <strong>Linux PAM</strong>, with the password chosen during setup.</p><a href={href} target="_blank" rel="noopener noreferrer" className="inline-block rounded-lg border border-glass-border px-3 py-2 font-medium">Open Proxmox</a></>}
    {data && !data.configured && <>
      {data.errors.map(message => <p key={message} role="status">{message}</p>)}
      {!data.ready && <p className="text-muted-foreground">The NAS remains usable. Xiaomi bootloader unlocking alone does not guarantee EL2/KVM availability; this setup does not change phone firmware.</p>}
      {data.busy ? <p role="status">Preparing Proxmox. You can continue using Homeio; no guest VM is started.</p> : data.ready && <form onSubmit={enable} className="space-y-2">
        <p>Create a separate Proxmox password. Your Homeio account stays separate.</p>
        <label className="block">Password<input type="password" autoComplete="new-password" minLength={8} maxLength={128} required value={password} onChange={e => setPassword(e.target.value)} className="mt-1 block w-full rounded-lg border border-glass-border bg-transparent p-2" /></label>
        <label className="block">Repeat password<input type="password" autoComplete="new-password" minLength={8} maxLength={128} required value={confirmation} onChange={e => setConfirmation(e.target.value)} className="mt-1 block w-full rounded-lg border border-glass-border bg-transparent p-2" /></label>
        <button disabled={pending} className="rounded-lg border border-glass-border px-3 py-2 font-medium disabled:opacity-50">{pending ? "Starting…" : "Set up Proxmox"}</button>
      </form>}
      {data.job.state === "failed" && <p role="alert">{data.job.error || "Setup did not finish."}</p>}
    </>}
  </section>;
}
