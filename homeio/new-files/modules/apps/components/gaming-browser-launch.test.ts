// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { openGamingBrowser } from "./gaming-browser-launch";

class Channel {
  static latest: Channel;
  onmessage?: (event: { data: unknown }) => void;
  postMessage = vi.fn(); close = vi.fn();
  constructor(public name: string) { Channel.latest = this; }
}
describe("browser launch handoff", () => {
  beforeEach(() => { vi.useFakeTimers(); vi.stubGlobal("BroadcastChannel", Channel); vi.spyOn(window, "open").mockReturnValue({} as Window); });
  afterEach(() => { vi.clearAllTimers(); vi.useRealTimers(); vi.unstubAllGlobals(); vi.restoreAllMocks(); });
  it("opens a real progress URL immediately, using random IDs that work on HTTP LAN origins", () => {
    openGamingBrowser("steam");
    const url = new URL(vi.mocked(window.open).mock.calls[0][0] as string);
    expect(url.pathname).toBe("/gaming-launcher.html"); expect(url.searchParams.get("app")).toBe("steam");
    expect(url.searchParams.get("launch")).toMatch(/^[0-9a-f]{32}$/);
  });
  it("replays completion if the child loads after the start request finishes", () => {
    const browser = openGamingBrowser("steam"); browser.ready(); Channel.latest.postMessage.mockClear();
    Channel.latest.onmessage?.({data:{state:"hello"}});
    expect(Channel.latest.postMessage).toHaveBeenCalledWith({state:"ready"});
  });
  it("keeps an error available to a late progress page instead of closing it", () => {
    const browser = openGamingBrowser("retroarch"); browser.fail("Unavailable"); Channel.latest.postMessage.mockClear();
    Channel.latest.onmessage?.({data:{state:"hello"}});
    expect(Channel.latest.postMessage).toHaveBeenCalledWith({state:"error",error:"Unavailable"});
  });
  it("reports blocked pop-ups and releases its channel", () => {
    vi.mocked(window.open).mockReturnValue(null);
    expect(() => openGamingBrowser("steam")).toThrow("bloqueou"); expect(Channel.latest.close).toHaveBeenCalled();
  });
});
