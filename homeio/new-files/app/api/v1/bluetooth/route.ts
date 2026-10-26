import { NextResponse } from "next/server";
import { requireApiSession } from "@/lib/server/modules/auth/api";
import { BluetoothError, getBluetoothManager } from "@/lib/server/modules/bluetooth/service.mjs";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const auth = await requireApiSession(request);
  if (auth.response) return auth.response;
  return NextResponse.json({ data: await getBluetoothManager().status() }, { headers: { "Cache-Control": "no-store" } });
}

export async function POST(request: Request) {
  const auth = await requireApiSession(request);
  if (auth.response) return auth.response;
  // Never let a different website control the NAS radio using the owner's cookie.
  const origin = request.headers.get("origin");
  let sameOrigin = false;
  try {
    const source = new URL(origin ?? "");
    sameOrigin = ["http:", "https:"].includes(source.protocol) && source.origin === origin && source.host === request.headers.get("host");
  } catch { /* A missing or malformed Origin is not a browser action. */ }
  if (!sameOrigin) {
    return NextResponse.json({ error: "Open Bluetooth from the Homeio desktop." }, { status: 403 });
  }
  try {
    const body = await request.text();
    if (body.length > 2048) return NextResponse.json({ error: "Request is too large." }, { status: 400 });
    const input: unknown = JSON.parse(body);
    return NextResponse.json({ data: await getBluetoothManager().act(input) }, { headers: { "Cache-Control": "no-store" } });
  } catch (error) {
    return NextResponse.json({ error: error instanceof BluetoothError ? error.message : "Invalid Bluetooth request." },
      { status: error instanceof BluetoothError ? error.status : 400 });
  }
}
