"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { SVGProps } from "react";
import { SETTINGS_PANEL_INSET } from "@/modules/settings/components/panel/surface";
import { cn } from "@/lib/utils";

type Device = { address: string; name: string; paired: boolean; trusted: boolean; connected: boolean; rssi: number | null };
type BluetoothStatus = {
  available: boolean;
  message?: string;
  adapter?: { name: string; powered: boolean; discovering: boolean; scanning: boolean };
  devices: Device[];
  operation?: { state: string; message: string } | null;
};
const button = "rounded-lg border border-glass-border bg-background/50 px-3 py-1.5 text-xs font-medium hover:bg-primary/15 disabled:cursor-wait disabled:opacity-40";

export function BluetoothIcon(props: SVGProps<SVGSVGElement>) {
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>
    <path d="m7 7 10 10-5 5V2l5 5L7 17" />
  </svg>;
}

export function BluetoothSection() {
  const [data, setData] = useState<BluetoothStatus | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [remove, setRemove] = useState<string | null>(null);
  const alive = useRef(true);
  const version = useRef(0);

  const refresh = useCallback(async () => {
    const current = version.current;
    try {
      const response = await fetch("/api/v1/bluetooth", { cache: "no-store" });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || "Could not read Bluetooth status.");
      if (alive.current && current === version.current) setData(result.data);
    } catch (cause) {
      if (alive.current) setError(cause instanceof Error ? cause.message : "Could not read Bluetooth status.");
    }
  }, []);

  useEffect(() => {
    alive.current = true;
    void refresh();
    const timer = setInterval(() => { if (!document.hidden) void refresh(); }, 3000);
    return () => { alive.current = false; clearInterval(timer); };
  }, [refresh]);

  async function act(action: string, extra: Record<string, unknown> = {}) {
    setBusy(true); setError(""); version.current++;
    try {
      const response = await fetch("/api/v1/bluetooth", {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ action, ...extra }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || "Bluetooth operation failed.");
      if (alive.current) { setData(result.data); setRemove(null); }
    } catch (cause) {
      if (alive.current) setError(cause instanceof Error ? cause.message : "Bluetooth operation failed.");
    } finally { version.current++; if (alive.current) setBusy(false); }
  }

  const pairing = data?.operation?.state === "pending";
  const powered = data?.adapter?.powered ?? false;
  const paired = data?.devices.filter(device => device.paired) ?? [];
  const nearby = data?.devices.filter(device => !device.paired) ?? [];

  function deviceRow(device: Device) {
    return (
      <div key={device.address} className="border-t border-glass-border/50 px-4 py-3 first:border-0">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="min-w-0">
            <div className="break-words text-sm font-medium">{device.name}</div>
            <div className="mt-1 text-xs text-muted-foreground">
              {device.connected ? "Connected" : device.paired ? "Paired · disconnected" : "Available to pair"}
            </div>
            <div className="mt-1 font-mono text-[10px] text-muted-foreground/60">{device.address}</div>
          </div>
          <div className="flex flex-wrap gap-2">
            <button className={button} disabled={busy || pairing || !powered}
              onClick={() => void act(device.connected ? "disconnect" : device.paired ? "connect" : "pair", { address: device.address })}>
              {device.connected ? "Disconnect" : device.paired ? "Connect" : "Pair controller"}
            </button>
            {device.paired && <button className={button} disabled={busy || pairing} onClick={() => setRemove(device.address)}>Forget</button>}
          </div>
        </div>
        {remove === device.address && <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
          <span>Forget this device? It will need pairing again.</span>
          <button className={button} disabled={busy} onClick={() => void act("remove", { address: device.address })}>Forget device</button>
          <button className={button} disabled={busy} onClick={() => setRemove(null)}>Cancel</button>
        </div>}
      </div>
    );
  }

  return (
    <div className="space-y-4" data-testid="nas-bluetooth-panel">
      <p className="text-xs leading-relaxed text-muted-foreground">Manage controllers connected to the NAS. The phone screen can stay off.</p>
      {error && <p role="alert" className="rounded-lg border border-status-red/30 bg-status-red/10 p-3 text-xs">{error}</p>}
      {!data && <p className="text-sm text-muted-foreground">Loading Bluetooth…</p>}
      {data && !data.available && <p role="status" className={cn(SETTINGS_PANEL_INSET, "p-4 text-sm")}>{data.message}</p>}
      {data?.available && <>
        <div className={cn(SETTINGS_PANEL_INSET, "flex flex-wrap items-center justify-between gap-3 p-4")}>
          <div><p className="text-sm font-medium">NAS Bluetooth</p><p className="mt-1 text-xs text-muted-foreground">{powered ? "On" : "Off"}</p></div>
          <button role="switch" aria-label="Bluetooth power" aria-checked={powered} className={button} disabled={busy || pairing}
            onClick={() => void act("power", { powered: !powered })}>{powered ? "Turn off" : "Turn on"}</button>
        </div>
        {data.operation && <div role="status" className={cn("rounded-lg border p-3 text-xs", data.operation.state === "error" ? "border-status-red/30" : "border-glass-border")}>
          {data.operation.message}
          {pairing && <button className={cn(button, "ml-3")} disabled={busy} onClick={() => void act("cancel")}>Cancel pairing</button>}
        </div>}
        <div><h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Paired devices</h3>
          <div className={SETTINGS_PANEL_INSET}>{paired.length ? paired.map(deviceRow) : <p className="p-4 text-xs text-muted-foreground">No paired controllers yet.</p>}</div>
        </div>
        <div>
          <div className="mb-2 flex items-center justify-between gap-2">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Nearby devices</h3>
            <button className={button} disabled={busy || pairing || !powered} onClick={() => void act(data.adapter?.scanning ? "stop-scan" : "scan")}>
              {data.adapter?.scanning ? "Stop search" : "Search for controllers"}
            </button>
          </div>
          <div className={SETTINGS_PANEL_INSET}>{nearby.length ? nearby.map(deviceRow) : <p className="p-4 text-xs text-muted-foreground">
            {data.adapter?.scanning ? "Searching… keep the controller in pairing mode. Search stops automatically after 45 seconds." : "Put your controller in pairing mode, then start a search."}
          </p>}</div>
        </div>
        <div className={cn(SETTINGS_PANEL_INSET, "space-y-2 p-4 text-xs leading-relaxed text-muted-foreground")}>
          <p>Xbox: switch on, then hold the pairing button until the Xbox light flashes quickly. The controller must support Bluetooth.</p>
          <p>PlayStation: hold Share + PS (DualShock 4) or Create + PS (DualSense) until the light flashes.</p>
          <p>When playing through Moonlight on a TV, pair the controller with the TV instead. Moonlight sends its inputs to the NAS.</p>
        </div>
      </>}
    </div>
  );
}
