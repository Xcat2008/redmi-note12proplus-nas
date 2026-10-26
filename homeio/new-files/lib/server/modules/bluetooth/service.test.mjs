import test from "node:test";
import assert from "node:assert/strict";
import { BluetoothManager, validateAction } from "./service.mjs";

const path = "/org/bluez/hci0/dev_AA_BB_CC_DD_EE_FF";
const address = "AA:BB:CC:DD:EE:FF";
const wrap = value => ({ value });
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

function fixture(options = {}) {
  let agent;
  const calls = [];
  const adapter = { Powered: wrap(true), Alias: wrap("NAS test radio"), Discovering: wrap(false) };
  const device = { Address: wrap(address), Name: wrap("Test controller"), Adapter: wrap("/org/bluez/hci0"),
    Paired: wrap(false), Connected: wrap(false), RSSI: wrap(-40), Trusted: wrap(false) };
  const record = { "/org/bluez/hci0": { "org.bluez.Adapter1": adapter }, [path]: { "org.bluez.Device1": device } };
  const iface = {
    GetManagedObjects: async () => record,
    RegisterAgent: async () => calls.push("agent"),
    SetDiscoveryFilter: async () => {},
    StartDiscovery: async () => { calls.push("scan"); adapter.Discovering.value = true; },
    StopDiscovery: async () => { calls.push("stop"); adapter.Discovering.value = false; },
    Pair: async () => { calls.push("pair"); await options.pair?.(); device.Paired.value = true; },
    CancelPairing: async () => calls.push("cancel"),
    Set: async (type, name, val) => { (type === "org.bluez.Adapter1" ? adapter : device)[name] = val; },
    Connect: async () => { calls.push("connect"); if (options.connectFail) throw Error("connect failed"); device.Connected.value = true; },
    Disconnect: async () => { device.Connected.value = false; },
    RemoveDevice: async target => { calls.push("remove"); delete record[target]; },
  };
  const bus = { export: (_, selectedAgent) => { agent = selectedAgent; }, on: () => {}, disconnect: () => {},
    getProxyObject: async () => ({ getInterface: () => iface }) };
  const manager = new BluetoothManager({ busFactory: () => bus, scanMs: 20, pairMs: 25 });
  return { manager, calls, device, adapter, get agent() { return agent; } };
}

test("rejects arbitrary commands and injected device addresses", () => {
  for (const input of [null, { action: "exec" }, { action: "pair", address: "x; rm /" }, { action: "power", powered: "false" }])
    assert.throws(() => validateAction(input));
  assert.equal(validateAction({ action: "pair", address: address.toLowerCase() }).address, address);
});

test("discovery survives requests but stops automatically", async () => {
  const f = fixture();
  await f.manager.act({ action: "scan" });
  assert.equal((await f.manager.status()).adapter.scanning, true);
  await delay(40);
  assert.equal((await f.manager.status()).adapter.scanning, false);
  assert.deepEqual(f.calls, ["scan", "stop"]);
  await f.manager.close();
});

test("selected controller pairs, is trusted and connects; unrelated agents are rejected", async () => {
  const f = fixture({ pair: () => delay(5) });
  await f.manager.act({ action: "pair", address });
  assert.throws(() => f.agent.RequestAuthorization("/org/bluez/unselected"));
  assert.doesNotThrow(() => f.agent.RequestAuthorization(path));
  await assert.rejects(f.manager.act({ action: "scan" }), /in progress/);
  await delay(15);
  assert.equal(f.device.Trusted.value, true);
  assert.equal(f.device.Connected.value, true);
  assert.equal((await f.manager.status()).operation.state, "success");
  assert.throws(() => f.agent.RequestAuthorization(path));
  await f.manager.close();
});

test("successful bond survives a connection failure", async () => {
  const f = fixture({ connectFail: true });
  await f.manager.act({ action: "pair", address });
  await delay(10);
  assert.equal(f.device.Paired.value, true);
  assert.equal((await f.manager.status()).operation.state, "success");
  assert.equal(f.calls.includes("remove"), false);
  await f.manager.close();
});

test("pairing timeout cancels pairing and frees the operation", async () => {
  const f = fixture({ pair: () => new Promise(() => {}) });
  await f.manager.act({ action: "pair", address });
  await delay(50);
  assert.equal((await f.manager.status()).operation.state, "error");
  assert.equal(f.calls.includes("cancel"), true);
  assert.equal(f.manager.busy, false);
  await f.manager.close();
});

test("disconnect and forget keep device lifecycle explicit", async () => {
  const f = fixture();
  f.device.Paired.value = true;
  await f.manager.act({ action: "connect", address });
  await f.manager.act({ action: "disconnect", address });
  assert.equal(f.device.Connected.value, false);
  await f.manager.act({ action: "remove", address });
  assert.equal((await f.manager.status()).devices.length, 0);
  await f.manager.close();
});
