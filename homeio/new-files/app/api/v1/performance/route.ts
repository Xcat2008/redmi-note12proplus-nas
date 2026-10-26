import { NextResponse } from "next/server";
import { requireApiSession } from "@/lib/server/modules/auth/api";
import { EnergyProfileError, getEnergyStatus, setEnergyProfile } from "@/lib/server/modules/system/energy-profiles";

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
    const input = JSON.parse(body) as { profile?: unknown };
    return NextResponse.json({ data: await setEnergyProfile(input?.profile) }, { headers: { "Cache-Control": "no-store" } });
  } catch (error) {
    return NextResponse.json({ error: error instanceof EnergyProfileError ? error.message : "Could not change the energy profile." },
      { status: error instanceof EnergyProfileError ? error.status : 502 });
  }
}
