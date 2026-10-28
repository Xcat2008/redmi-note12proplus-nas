"use client";
import { useEffect, useState } from "react";
import { openGamingBrowser } from "./gaming-browser-launch";
import * as ContextMenu from "@radix-ui/react-context-menu";
type Status = { installed: boolean; running: boolean; startupEnabled: boolean; retroarchInstalled: boolean; retroarchRunning: boolean };
export function SteamShortcut({ iconClass, kind = "steam" }: { iconClass: string; kind?: "steam" | "retroarch" }) {
  const [state, setState] = useState<Status | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const name = kind === "steam" ? "Steam" : "RetroArch";
  const running = kind === "steam" ? state?.running : state?.retroarchRunning;
  const startAction = kind === "steam" ? "steam-start" : "retroarch-focus";
  const stopAction = kind === "steam" ? "steam-stop" : "retroarch-stop";
  useEffect(() => {
    let live = true;
    const refresh = async () => { try { const r = await fetch("/api/v1/gaming-apps", { cache: "no-store" }); const body = await r.json(); if (live && r.ok) setState(body.data); } catch {} };
    void refresh(); const timer = setInterval(() => { if (!document.hidden) void refresh(); }, 15000);
    return () => { live = false; clearInterval(timer); };
  }, []);
  async function action(value: "steam-start" | "steam-stop" | "retroarch-focus" | "retroarch-stop", open = false) {
    let browser: ReturnType<typeof openGamingBrowser> | undefined;
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 75000);
    setPending(true); setError("");
    try {
      if (open) browser = openGamingBrowser(kind);
      const r = await fetch("/api/v1/gaming-apps", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ action: value }), signal: controller.signal });
      const body = await r.json(); if (!r.ok) throw new Error(body.error || "The application action failed.");
      setState(body.data);
      if (open && body.data?.focused !== true) throw new Error("O serviço arrancou, mas a janela ainda não está pronta. Aguarda um pouco e tenta novamente.");
      browser?.ready();
    } catch (cause) {
      const message = cause instanceof Error && cause.name === "AbortError" ? "O arranque demorou demasiado. Verifica o estado da aplicação antes de tentar novamente." : cause instanceof Error ? cause.message : "The application action failed.";
      browser?.fail(message); setError(message);
    }
    finally { window.clearTimeout(timeout); setPending(false); }
  }
  if (!(kind === "steam" ? state?.installed : state?.retroarchInstalled)) return null;
  return <>
    <ContextMenu.Root>
      <ContextMenu.Trigger asChild>
        <button aria-label={`Open ${name}`} title={pending ? `Starting ${name}…` : running ? `${name} · Running` : `${name} · Stopped`}
          disabled={pending} onClick={() => void action(startAction, true)}
          className="group flex cursor-pointer flex-col items-center gap-2 rounded-xl p-2 hover:bg-foreground/5 disabled:opacity-50">
          <div className={`${iconClass} relative flex items-center justify-center overflow-hidden border border-glass-border bg-[#10263f] shadow-lg shadow-black/20`}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={kind === "steam" ? "/steam-icon.png" : "/retroarch-icon.svg"} alt={name} className="h-full w-full object-contain p-1.5" />
            <span aria-hidden="true" className={`absolute bottom-1 right-1 size-2 rounded-full ${running ? "bg-green-400" : "bg-zinc-400"}`} />
          </div>
          <span className="max-w-[4.5rem] truncate text-center text-2xs font-medium leading-tight tracking-tight text-foreground/80">{name}</span>
        </button>
      </ContextMenu.Trigger>
      <ContextMenu.Portal><ContextMenu.Content className="z-[250] min-w-40 rounded-xl border border-glass-border bg-popover p-1.5 text-sm text-popover-foreground shadow-xl">
        <ContextMenu.Item disabled={pending} onSelect={() => void action(startAction, true)} className="cursor-pointer rounded-lg px-3 py-2 outline-none data-[highlighted]:bg-foreground/10">Open {name}</ContextMenu.Item>
        <ContextMenu.Item disabled={pending || running} onSelect={() => void action(startAction)} className="cursor-pointer rounded-lg px-3 py-2 outline-none data-[highlighted]:bg-foreground/10 data-[disabled]:opacity-40">Start</ContextMenu.Item>
        <ContextMenu.Item disabled={pending || !running} onSelect={() => void action(stopAction)} className="cursor-pointer rounded-lg px-3 py-2 outline-none data-[highlighted]:bg-foreground/10 data-[disabled]:opacity-40">Stop</ContextMenu.Item>
      </ContextMenu.Content></ContextMenu.Portal>
    </ContextMenu.Root>
    {error && <p role="alert" className="fixed bottom-24 left-1/2 z-[260] max-w-sm -translate-x-1/2 rounded-xl border border-status-red/40 bg-popover p-4 text-sm">{error}<button aria-label="Dismiss error" onClick={() => setError("")} className="ml-3">×</button></p>}
  </>;
}
