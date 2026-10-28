export type GamingLaunchKind = "steam" | "retroarch";

/** The new tab navigates itself, avoiding a delayed cross-origin window write. */
export function openGamingBrowser(kind: GamingLaunchKind) {
  const id = Array.from(crypto.getRandomValues(new Uint8Array(16)), (value) => value.toString(16).padStart(2, "0")).join("");
  const url = new URL("/gaming-launcher.html", window.location.origin);
  url.searchParams.set("app", kind);
  url.searchParams.set("launch", id);
  const channel = typeof BroadcastChannel !== "undefined" ? new BroadcastChannel(`gaming-launch-${id}`) : null;
  let state: { state: "pending" | "ready" | "error"; error?: string } = { state: "pending" };
  if (channel) channel.onmessage = (event) => {
    if (event.data?.state === "hello") channel?.postMessage(state);
  };
  const popup = window.open(url.href, `redmi-${kind}`);
  if (!popup) {
    channel?.close();
    throw new Error("O browser bloqueou o separador. Permite pop-ups para o Homeio e volta a abrir a aplicação.");
  }
  const cleanup = window.setTimeout(() => channel?.close(), 90000);
  return {
    ready() { state = { state: "ready" }; channel?.postMessage(state); },
    fail(error: string) { state = { state: "error", error }; channel?.postMessage(state); },
    close() { window.clearTimeout(cleanup); channel?.close(); },
  };
}
