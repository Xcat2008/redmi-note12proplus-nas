import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { runInNewContext } from "node:vm";

const page = readFileSync(new URL("../../../public/proxmox-launcher.html", import.meta.url), "utf8");
const script = page.match(/<script>([\s\S]*?)<\/script>/)?.[1];
assert.ok(script);

async function fixture(replies: Array<{ status: number; data?: object }>, frame = false) {
  const calls: Array<{ url: string; method: string; body?: string }> = [];
  const redirects: string[] = [];
  const handlers: Record<string, () => Promise<void>> = {};
  const state = { textContent: "" };
  const button = { hidden: true, disabled: false, addEventListener: (name: string, fn: () => Promise<void>) => { handlers[name] = fn; } };
  const win = { top: null as unknown, self: null as unknown, location: { href: "http://nas.example.invalid/proxmox-launcher.html?from=settings#local", replace: (url: string) => redirects.push(url) } };
  win.self = win; win.top = frame ? {} : win;
  runInNewContext(script!, {
    window: win, document: { hidden: false, getElementById: (id: string) => id === "state" ? state : button },
    URL, setInterval: () => 0,
    fetch: async (url: string, options: { method?: string; body?: string } = {}) => {
      calls.push({ url, method: options.method ?? "GET", body: options.body });
      const reply = replies.shift();
      assert.ok(reply, "Unexpected network request");
      return { status: reply.status, ok: reply.status >= 200 && reply.status < 300, json: async () => ({ data: reply.data }) };
    },
  });
  const settle = () => new Promise<void>(resolve => setImmediate(resolve));
  await settle(); await settle();
  return { calls, redirects, state, button, handlers, settle };
}

test("opening a stopped panel only reads status, and a deliberate click starts it", async () => {
  const f = await fixture([
    { status: 200, data: { configured: true, running: false, starting: false, webReady: false } },
    { status: 202, data: { configured: true, starting: true } },
    { status: 200, data: { configured: true, running: true, webReady: true, webPort: 1234 } },
  ]);
  assert.deepEqual(f.calls.map(x => x.method), ["GET"]);
  assert.equal(f.button.hidden, false);
  assert.equal(f.redirects.length, 0);
  await f.handlers.click();
  assert.deepEqual(f.calls.map(x => x.method), ["GET", "POST", "GET"]);
  assert.equal(f.calls[1].body, JSON.stringify({ action: "start" }));
  assert.deepEqual(f.redirects, ["https://nas.example.invalid:8006/"]);
});

test("a ready service opens directly without a start mutation", async () => {
  const f = await fixture([{ status: 200, data: { configured: true, running: true, webReady: true } }]);
  assert.deepEqual(f.calls.map(x => x.method), ["GET"]);
  assert.deepEqual(f.redirects, ["https://nas.example.invalid:8006/"]);
});

test("an unauthenticated visitor neither starts a service nor opens Proxmox", async () => {
  const f = await fixture([{ status: 401 }]);
  assert.equal(f.calls.length, 1);
  assert.equal(f.redirects.length, 0);
  assert.match(f.state.textContent, /conta Homeio/);
});

test("embedded pages do not query or start the component", async () => {
  const f = await fixture([], true);
  assert.equal(f.calls.length, 0);
  assert.equal(f.redirects.length, 0);
});
