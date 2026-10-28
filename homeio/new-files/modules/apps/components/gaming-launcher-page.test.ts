// @vitest-environment node
import { readFileSync } from "node:fs";
import vm from "node:vm";
import { describe, expect, it, vi } from "vitest";
const script = readFileSync("public/gaming-launcher.js", "utf8");
function page(query = "?app=steam&launch=" + "a".repeat(32)) {
  const elements = Object.fromEntries(["title","status","error","start","stream"].map(id => [id, {textContent:"",hidden:true,disabled:false,href:"",addEventListener:vi.fn()}]));
  let receiver: {onmessage?: (e: {data: unknown}) => void} = {};
  const channel = {postMessage:vi.fn(),close:vi.fn()};
  const timers: Array<() => void> = [];
  const replace = vi.fn(); const fetch = vi.fn();
  const context = vm.createContext({ URL, URLSearchParams, AbortController,
    document:{getElementById:(id:string)=>elements[id],title:""},
    window:{location:{search:query,href:"http://nas.test/gaming-launcher.html"+query,replace},addEventListener:vi.fn()},
    BroadcastChannel:class { constructor(){receiver=this;Object.assign(this,channel);} },
    setInterval:vi.fn(),clearInterval:vi.fn(),clearTimeout:vi.fn(),setTimeout:(fn:()=>void)=>{timers.push(fn);return timers.length;},fetch });
  vm.runInContext(script,context);
  return {elements,receiver,channel,timers,replace,fetch};
}
describe("launcher page", () => {
  it("never starts a service from a GET navigation", () => { const p=page();expect(p.fetch).not.toHaveBeenCalled();expect(p.channel.postMessage).toHaveBeenCalledWith({state:"hello"}); });
  it.each(["steam", "retroarch"])("opens %s with its own identity without leaking the launch token", (app) => {
    const p=page("?app="+app+"&launch="+"a".repeat(32));p.receiver.onmessage?.({data:{state:"ready"}});
    expect(p.replace).toHaveBeenCalledWith("https://nas.test:3443/?app="+app);expect(p.channel.close).toHaveBeenCalled();
  });
  it("shows backend failures as text with an explicit retry", () => {
    const p=page();p.receiver.onmessage?.({data:{state:"error",error:"<service unavailable>"}});
    expect(p.elements.error.textContent).toBe("<service unavailable>");expect(p.elements.start.hidden).toBe(false);expect(p.replace).not.toHaveBeenCalled();
  });
  it("turns a missing parent response into a bounded error", () => {const p=page();p.timers[0]();expect(p.elements.error.hidden).toBe(false);expect(p.elements.start.hidden).toBe(false);});
  it("does not start automatically when opened directly", () => {const p=page("?app=steam");expect(p.elements.start.hidden).toBe(false);expect(p.fetch).not.toHaveBeenCalled();});
  it("rejects unknown app names rather than treating them as service actions", () => {const p=page("?app=other");expect(p.elements.title.textContent).toBe("Aplicação desconhecida");expect(p.fetch).not.toHaveBeenCalled();});
});
