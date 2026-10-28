const params = new URLSearchParams(window.location.search);
const kind = params.get("app");
const valid = kind === "steam" || kind === "retroarch";
const name = kind === "steam" ? "Steam" : "RetroArch";
const title = document.getElementById("title");
const status = document.getElementById("status");
const error = document.getElementById("error");
const start = document.getElementById("start");
const stream = document.getElementById("stream");
const target = new URL(window.location.href);
target.protocol = "https:"; target.port = "3443"; target.pathname = "/"; target.search = ""; target.hash = "";
if (valid) target.searchParams.set("app", kind);
stream.href = target.href;
let channel, helloTimer, deadline, settled = false;
function cleanup() {
  clearInterval(helloTimer); clearTimeout(deadline); channel?.close(); channel = undefined;
}
function failed(message) {
  settled = true; cleanup();
  title.textContent = `Não foi possível abrir ${name}`;
  status.textContent = "Podes tentar novamente ou abrir diretamente a sessão partilhada.";
  error.textContent = message; error.hidden = false; start.hidden = false; start.disabled = false; stream.hidden = false;
}
function ready() {
  settled = true; cleanup(); title.textContent = `A abrir ${name}…`;
  status.textContent = "A aplicação está pronta. A ligar à sessão de jogos…";
  stream.hidden = false;
  window.location.replace(target.href);
}
if (!valid) {
  title.textContent = "Aplicação desconhecida";
  status.textContent = "Abre a Steam ou o RetroArch a partir do Homeio.";
} else {
  document.title = `${name} · Homeio`;
  title.textContent = `A iniciar ${name}…`;
  start.textContent = `Iniciar e abrir ${name}`;
  // A GET navigation never starts services. Only the Homeio click or this explicit button sends POST.
  start.addEventListener("click", async () => {
    cleanup(); settled = false; start.disabled = true; error.hidden = true;
    title.textContent = `A iniciar ${name}…`;
    status.textContent = "A primeira abertura pode demorar cerca de um minuto.";
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 75000);
    try {
      const response = await fetch("/api/v1/gaming-apps", {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({action:kind === "steam" ? "steam-start" : "retroarch-focus"}),signal:controller.signal});
      const body = await response.json();
      if (!response.ok) throw new Error(body.error || "A aplicação não respondeu.");
      if (body.data?.focused !== true) throw new Error("O serviço arrancou, mas a janela ainda não está pronta. Aguarda um pouco e tenta novamente.");
      ready();
    } catch (cause) { failed(cause.name === "AbortError" ? "O arranque demorou demasiado. Verifica o estado no Homeio antes de tentar novamente." : cause.message || "Não foi possível ligar à NAS."); }
    finally { clearTimeout(timeout); }
  });
  const id = params.get("launch");
  if (id && /^[a-f0-9]{32}$/i.test(id) && typeof BroadcastChannel !== "undefined") {
    channel = new BroadcastChannel(`gaming-launch-${id}`);
    channel.onmessage = (event) => {
      if (settled) return;
      if (event.data?.state === "ready") ready();
      else if (event.data?.state === "error") failed(String(event.data.error || "A aplicação não respondeu."));
      else if (event.data?.state === "pending") status.textContent = "A preparar a janela. A primeira abertura pode demorar cerca de um minuto.";
    };
    helloTimer = setInterval(() => channel?.postMessage({state:"hello"}), 1000);
    channel.postMessage({state:"hello"});
    deadline = setTimeout(() => failed("Não recebemos a confirmação de arranque. Verifica o Homeio ou tenta novamente."), 80000);
  } else {
    title.textContent = `Abrir ${name}`;
    status.textContent = "Carrega no botão para iniciar a aplicação na NAS e abrir a sessão no browser.";
    start.hidden = false;
  }
}
window.addEventListener("pagehide", cleanup);
