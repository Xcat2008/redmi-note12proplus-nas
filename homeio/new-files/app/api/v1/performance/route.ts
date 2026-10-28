import { NextResponse } from "next/server";
import { requireApiSession } from "@/lib/server/modules/auth/api";
import { EnergyProfileError, getEnergyStatus, setEnergyProfile } from "@/lib/server/modules/system/energy-profiles";
import { memoryExtension, MemoryExtensionError } from "@/lib/server/modules/system/memory-extension";
import { batteryCharge, BatteryChargeError } from "@/lib/server/modules/system/battery-charge";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const auth = await requireApiSession(request);
  if (auth.response) return auth.response;
  return NextResponse.json({ data: await getEnergyStatus() }, { headers: { "Cache-Control": "no-store" } });
}
export async function POST(request: Request) {
  const auth = await requireApiSession(request);
  if (auth.response) return auth.response;
  const origin = request.headers.get("origin");
  let sameOrigin = false;
  try { const source = new URL(origin ?? ""); sameOrigin = ["http:", "https:"].includes(source.protocol) && source.origin === origin && source.host === request.headers.get("host"); } catch {}
  if (!sameOrigin) return NextResponse.json({ error: "Open Performance from Homeio Settings." }, { status: 403 });
  try {
    const body = await request.text();
    if (body.length > 2048) throw new EnergyProfileError("Request is too large.");
    const input = JSON.parse(body) as { profile?: unknown; memoryExtension?: unknown; batteryCare?: unknown };
    if (!input || typeof input !== "object" || Array.isArray(input)) throw new EnergyProfileError("Choose one performance setting.");
    if (["profile", "memoryExtension", "batteryCare"].filter(key => Object.hasOwn(input, key)).length !== 1) throw new EnergyProfileError("Change one setting at a time.");
    if (Object.hasOwn(input, "batteryCare")) {
      if (typeof input.batteryCare !== "boolean") throw new EnergyProfileError("Choose whether to enable battery care.");
      await batteryCharge(input.batteryCare ? "enable" : "disable");
      return NextResponse.json({ data: await getEnergyStatus() }, { headers: { "Cache-Control": "no-store" } });
    }
    if (Object.hasOwn(input, "memoryExtension")) {
      if (typeof input.memoryExtension !== "boolean" || Object.hasOwn(input, "profile")) throw new EnergyProfileError("Choose whether to enable storage extension.");
      await memoryExtension(input.memoryExtension ? "enable" : "disable");
      return NextResponse.json({ data: await getEnergyStatus() }, { headers: { "Cache-Control": "no-store" } });
    }
    return NextResponse.json({ data: await setEnergyProfile(input?.profile) }, { headers: { "Cache-Control": "no-store" } });
  } catch (error) {
    return NextResponse.json({ error: error instanceof EnergyProfileError || error instanceof MemoryExtensionError || error instanceof BatteryChargeError ? error.message : "Could not change the performance setting." },
      { status: error instanceof EnergyProfileError ? error.status : error instanceof MemoryExtensionError || error instanceof BatteryChargeError ? 409 : 502 });
  }
}
