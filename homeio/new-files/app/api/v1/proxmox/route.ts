import { NextResponse } from "next/server";
import { requireApiSession } from "@/lib/server/modules/auth/api";
import { proxmoxSetup } from "@/lib/server/modules/system/proxmox-setup";
export const runtime = "nodejs";
export const dynamic = "force-dynamic";
const noStore = { "Cache-Control": "no-store" };
export async function GET(request: Request) {
  const auth = await requireApiSession(request);
  if (auth.response) return auth.response;
  try { return NextResponse.json({ data: await proxmoxSetup("status") }, { headers: noStore }); }
  catch { return NextResponse.json({ error: "Optional Proxmox setup is unavailable." }, { status: 503, headers: noStore }); }
}
export async function POST(request: Request) {
  const auth = await requireApiSession(request);
  if (auth.response) return auth.response;
  const origin = request.headers.get("origin");
  let sameOrigin = false;
  try { const source = new URL(origin ?? ""); sameOrigin = ["http:", "https:"].includes(source.protocol) && source.origin === origin && source.host === request.headers.get("host"); } catch {}
  if (!sameOrigin) return NextResponse.json({ error: "Open Proxmox setup from Homeio Settings." }, { status: 403 });
  let password: string;
  try {
    const raw = await request.text();
    if (raw.length > 2048) throw new Error();
    const input: unknown = JSON.parse(raw);
    if (!input || typeof input !== "object" || Array.isArray(input) || Object.keys(input).join() !== "password") throw new Error();
    const value = (input as { password: unknown }).password;
    if (typeof value !== "string" || value.length < 8 || value.length > 128 || /[\u0000-\u001f]/.test(value)) throw new Error();
    password = value;
  } catch { return NextResponse.json({ error: "Choose a password with 8–128 characters." }, { status: 400 }); }
  try { return NextResponse.json({ data: await proxmoxSetup("enable", password) }, { status: 202, headers: noStore }); }
  catch (error) { return NextResponse.json({ error: error instanceof Error ? error.message : "Could not start Proxmox setup." }, { status: 409, headers: noStore }); }
}
