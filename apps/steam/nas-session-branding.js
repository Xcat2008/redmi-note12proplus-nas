(() => {
  const app = new URLSearchParams(window.location.search).get("app");
  const name = app === "steam" ? "Steam" : app === "retroarch" ? "RetroArch" : "NAS · Sessão de jogos";
  const sync = () => { if (document.title !== name) document.title = name; };
  sync();
  const title = document.querySelector("title");
  if (title) new MutationObserver(sync).observe(title, { childList: true, subtree: true, characterData: true });
  for (const old of document.querySelectorAll('link[rel~="icon"],link[rel="apple-touch-icon"]')) old.remove();
  const icon = document.createElement("link");
  icon.rel = "icon";
  icon.href = app === "steam" ? "/nas-steam-icon.png" : app === "retroarch" ? "/nas-retroarch-icon.svg" : "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 48 48'%3E%3Crect width='48' height='48' rx='10' fill='%23101827'/%3E%3Cpath d='M10 22 24 10l14 12v16H10Z' fill='%235594df'/%3E%3C/svg%3E";
  document.head.appendChild(icon);
})();
