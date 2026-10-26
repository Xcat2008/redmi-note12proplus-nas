import dbus from "dbus-next";

const SERVICE = "org.bluez";
const ADAPTER = "org.bluez.Adapter1";
const DEVICE = "org.bluez.Device1";
const PROPERTIES = "org.freedesktop.DBus.Properties";
const AGENT_PATH = "/org/homeio/BluetoothAgent";
const addressPattern = /^(?:[A-F0-9]{2}:){5}[A-F0-9]{2}$/i;
const value = (entry, fallback = null) => entry?.value ?? fallback;

export class BluetoothError extends Error {
  constructor(message, status = 400) {
    super(message);
    this.status = status;
  }
}

export function validateAction(input) {
  const actions = ["scan", "stop-scan", "power", "pair", "cancel", "connect", "disconnect", "remove"];
  if (!input || !actions.includes(input.action)) throw new BluetoothError("Unknown Bluetooth action.");
  if (["pair", "connect", "disconnect", "remove"].includes(input.action) &&
      (typeof input.address !== "string" || !addressPattern.test(input.address))) {
    throw new BluetoothError("Select a device from the Bluetooth list.");
  }
  if (input.action === "power" && typeof input.powered !== "boolean") {
    throw new BluetoothError("A Bluetooth power state is required.");
  }
  return { action: input.action, address: input.address?.toUpperCase(), powered: input.powered };
}

export function describeDevice(path, props) {
  return {
    address: value(props.Address, ""),
    name: value(props.Name, value(props.Alias, value(props.Address, "Bluetooth device"))),
    paired: value(props.Paired, false),
    connected: value(props.Connected, false),
    trusted: value(props.Trusted, false),
    icon: value(props.Icon, ""),
    rssi: value(props.RSSI),
    path,
  };
}

function readableError(error) {
  const text = String(error?.type || error?.message || error);
  if (/AuthenticationRejected|AuthenticationCanceled|AuthenticationFailed/.test(text))
    return "Pairing was not accepted. Put the controller in pairing mode and try again.";
  if (/NotReady/.test(text)) return "Bluetooth is off or the radio is not ready.";
  if (/ConnectionAttemptFailed|br-connection|NotAvailable/.test(text))
    return "The controller did not connect. Check that it is awake and not connected to another device.";
  if (/InProgress/.test(text)) return "Another Bluetooth operation is still in progress.";
  if (/timeout|TimedOut|NoReply/.test(text)) return "Bluetooth timed out. Put the controller in pairing mode and try again.";
  return error instanceof BluetoothError ? error.message : "Bluetooth could not complete the operation. Try again with the controller nearby.";
}

class PairingAgent extends dbus.interface.Interface {
  constructor(manager) {
    super("org.bluez.Agent1");
    this.manager = manager;
  }
  assertSelected(path) {
    if (!this.manager.pairingPath || path !== this.manager.pairingPath) {
      throw new dbus.DBusError("org.bluez.Error.Rejected", "Device was not selected in Homeio");
    }
  }
  Release() { this.manager.agentRegistered = false; }
  Cancel() {}
  RequestAuthorization(path) { this.assertSelected(path); }
  RequestConfirmation(path) { this.assertSelected(path); }
  AuthorizeService(path) { this.assertSelected(path); }
  RequestPinCode(path) {
    this.assertSelected(path);
    throw new dbus.DBusError("org.bluez.Error.Rejected", "This panel supports controllers with automatic pairing, not PIN entry");
  }
  RequestPasskey(path) { return this.RequestPinCode(path); }
  DisplayPinCode(path) { this.assertSelected(path); }
  DisplayPasskey(path) { this.assertSelected(path); }
}
PairingAgent.configureMembers({ methods: {
  Release: {}, Cancel: {},
  RequestAuthorization: { inSignature: "o" },
  RequestConfirmation: { inSignature: "ou" },
  AuthorizeService: { inSignature: "os" },
  RequestPinCode: { inSignature: "o", outSignature: "s" },
  RequestPasskey: { inSignature: "o", outSignature: "u" },
  DisplayPinCode: { inSignature: "os" },
  DisplayPasskey: { inSignature: "ouq" },
} });

export class BluetoothManager {
  constructor({ busFactory = () => dbus.systemBus(), scanMs = 45000, pairMs = 60000 } = {}) {
    this.busFactory = busFactory;
    this.scanMs = scanMs;
    this.pairMs = pairMs;
    this.bus = null;
    this.scanTimer = null;
    this.scanAdapter = null;
    this.pairingPath = null;
    this.agentRegistered = false;
    this.busy = false;
    this.operation = null;
  }
  getBus() {
    if (!this.bus) {
      const bus = this.busFactory();
      this.bus = bus;
      this.agent = new PairingAgent(this);
      bus.export(AGENT_PATH, this.agent);
      bus.on("error", () => {
        this.agentRegistered = false;
        if (this.bus === bus) { this.bus = null; bus.disconnect(); }
      });
    }
    return this.bus;
  }
  async proxy(path, iface) {
    const object = await this.getBus().getProxyObject(SERVICE, path);
    return object.getInterface(iface);
  }
  async bounded(promise, milliseconds = 10000) {
    let timer;
    try {
      return await Promise.race([promise, new Promise((_, reject) => {
        timer = setTimeout(() => reject(new BluetoothError("Bluetooth timed out.", 504)), milliseconds);
        timer.unref?.();
      })]);
    } finally { clearTimeout(timer); }
  }
  async objects() {
    const manager = await this.proxy("/", "org.freedesktop.DBus.ObjectManager");
    return this.bounded(manager.GetManagedObjects());
  }
  async status() {
    try {
      const objects = await this.objects();
      const adapter = Object.entries(objects).find(([, interfaces]) => interfaces[ADAPTER]);
      if (!adapter) return { available: false, message: "No Bluetooth adapter is available.", devices: [], operation: this.operation };
      const [path, interfaces] = adapter;
      const props = interfaces[ADAPTER];
      return {
        available: true,
        adapter: { name: value(props.Alias, "NAS Bluetooth"), powered: value(props.Powered, false),
          discovering: value(props.Discovering, false), scanning: this.scanAdapter === path },
        devices: Object.entries(objects)
          .filter(([, record]) => record[DEVICE] && value(record[DEVICE].Adapter) === path)
          .map(([devicePath, record]) => describeDevice(devicePath, record[DEVICE]))
          .filter(device => device.paired || device.connected || (value(props.Powered, false) && device.rssi !== null))
          .sort((a, b) => Number(b.connected) - Number(a.connected) || Number(b.paired) - Number(a.paired) || a.name.localeCompare(b.name))
          .map(({ path: _path, ...device }) => device),
        operation: this.operation,
      };
    } catch {
      return { available: false, message: "The NAS Bluetooth service is unavailable. Check the Bluetooth service and radio firmware.",
        devices: [], operation: this.operation };
    }
  }
  async selected(address) {
    const objects = await this.objects();
    const adapter = Object.entries(objects).find(([, interfaces]) => interfaces[ADAPTER]);
    if (!adapter) throw new BluetoothError("No Bluetooth adapter is available.", 503);
    const [adapterPath, interfaces] = adapter;
    if (!address) return { adapterPath, props: interfaces[ADAPTER] };
    const device = Object.entries(objects).find(([, record]) => record[DEVICE] &&
      value(record[DEVICE].Adapter) === adapterPath && value(record[DEVICE].Address, "").toUpperCase() === address);
    if (!device) throw new BluetoothError("Device is no longer available. Search again.", 404);
    return { adapterPath, path: device[0], props: device[1][DEVICE] };
  }
  async stopScan() {
    clearTimeout(this.scanTimer);
    this.scanTimer = null;
    const path = this.scanAdapter;
    this.scanAdapter = null;
    if (path) {
      const adapter = await this.proxy(path, ADAPTER);
      await this.bounded(adapter.StopDiscovery());
    }
  }
  async pair(path, props, address) {
    this.pairingPath = path;
    try {
      await this.stopScan();
      const device = await this.proxy(path, DEVICE);
      if (!value(props.Paired, false)) {
        // This agent belongs only to our D-Bus connection. It never replaces the phone's default agent.
        const agentManager = await this.proxy("/org/bluez", "org.bluez.AgentManager1");
        try { await this.bounded(agentManager.RegisterAgent(AGENT_PATH, "NoInputNoOutput")); }
        catch (error) { if (!String(error.type).endsWith("AlreadyExists")) throw error; }
        this.agentRegistered = true;
        try { await this.bounded(device.Pair(), this.pairMs); }
        catch (error) { await this.bounded(device.CancelPairing(), 3000).catch(() => {}); throw error; }
      }
      const properties = await this.proxy(path, PROPERTIES);
      await this.bounded(properties.Set(DEVICE, "Trusted", new dbus.Variant("b", true)));
      try {
        await this.bounded(device.Connect(), 15000);
        this.operation = { action: "pair", address, state: "success", message: "Controller paired and connected." };
      } catch {
        this.operation = { action: "pair", address, state: "success", message: "Controller paired. Wake it up and choose Connect if it is not connected yet." };
      }
    } catch (error) {
      this.operation = { action: "pair", address, state: "error", message: readableError(error) };
    } finally {
      this.pairingPath = null;
      this.busy = false;
    }
  }
  async act(input) {
    const command = validateAction(input);
    if (command.action === "cancel") {
      if (this.pairingPath) {
        const device = await this.proxy(this.pairingPath, DEVICE);
        await this.bounded(device.CancelPairing());
      }
      return this.status();
    }
    if (command.action === "stop-scan") { await this.stopScan(); return this.status(); }
    if (this.busy) throw new BluetoothError("Another Bluetooth operation is still in progress.", 409);
    this.busy = true;
    let backgroundPair = false;
    try {
      const selected = await this.selected(command.address);
      if (command.action !== "power" && !value((await this.selected()).props.Powered, false))
        throw new BluetoothError("Turn on Bluetooth before continuing.");
      if (command.action === "pair") {
        this.operation = { action: "pair", address: command.address, state: "pending", message: "Pairing controller…" };
        backgroundPair = true;
        void this.pair(selected.path, selected.props, command.address);
      } else if (command.action === "scan") {
        await this.stopScan();
        const adapter = await this.proxy(selected.adapterPath, ADAPTER);
        await this.bounded(adapter.SetDiscoveryFilter({ Transport: new dbus.Variant("s", "auto"), DuplicateData: new dbus.Variant("b", false) }));
        await this.bounded(adapter.StartDiscovery());
        this.scanAdapter = selected.adapterPath;
        this.scanTimer = setTimeout(() => { void this.stopScan().catch(() => {}); }, this.scanMs);
        this.scanTimer.unref?.();
        this.operation = null;
      } else if (command.action === "power") {
        if (!command.powered) await this.stopScan();
        const properties = await this.proxy(selected.adapterPath, PROPERTIES);
        await this.bounded(properties.Set(ADAPTER, "Powered", new dbus.Variant("b", command.powered)));
        this.operation = null;
      } else if (command.action === "remove") {
        const adapter = await this.proxy(selected.adapterPath, ADAPTER);
        await this.bounded(adapter.RemoveDevice(selected.path));
        this.operation = { action: "remove", state: "success", message: "Device forgotten." };
      } else {
        if (command.action === "connect" && !value(selected.props.Paired, false))
          throw new BluetoothError("Pair this device first.");
        const device = await this.proxy(selected.path, DEVICE);
        await this.bounded(command.action === "connect" ? device.Connect() : device.Disconnect(), 15000);
        this.operation = { action: command.action, state: "success", message: command.action === "connect" ? "Device connected." : "Device disconnected." };
      }
      return this.status();
    } catch (error) {
      throw new BluetoothError(readableError(error), error.status || 502);
    } finally { if (!backgroundPair) this.busy = false; }
  }
  async close() {
    await this.stopScan().catch(() => {});
    this.bus?.disconnect();
    this.bus = null;
  }
}

// Keep discovery and the pairing agent alive across API requests and development reloads.
const key = Symbol.for("homeio.nas.bluetooth");
export function getBluetoothManager() {
  return globalThis[key] ??= new BluetoothManager();
}
