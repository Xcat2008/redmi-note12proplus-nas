import { NextResponse } from "next/server";
import { requireApiSession } from "@/lib/server/modules/auth/api";
import { controlGamingApp, GamingAppError } from "@/lib/server/modules/system/gaming-apps";
export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export async function GET(request: Request) {
  const auth = await requireApiSession(request); if (auth.response) return auth.response;
  try { return NextResponse.json({ data: await controlGamingApp("status") }, { headers: { "Cache-Control": "no-store" } }); }
  catch { return NextResponse.json({ error: "Application status is unavailable." }, { status: 503 }); }
}
export async function POST(request: Request) {
  const auth = await requireApiSession(request); if (auth.response) return auth.response;
  const origin = request.headers.get("origin"); let sameOrigin = false;
  try { const u = new URL(origin ?? ""); sameOrigin = ["http:", "https:"].includes(u.protocol) && u.origin === origin && u.host === request.headers.get("host"); } catch {}
  if (!sameOrigin) return NextResponse.json({ error: "Open the application from Homeio." }, { status: 403 });
  try {
    const body = await request.text(); if (body.length > 512) return NextResponse.json({ error: "Invalid request." }, { status: 400 });
    const input = JSON.parse(body) as { action?: unknown };
    if (typeof input?.action !== "string" || !["steam-start", "steam-stop", "retroarch-focus", "retroarch-stop"].includes(input.action)) return NextResponse.json({ error: "Choose an application action." }, { status: 400 });
    return NextResponse.json({ data: await controlGamingApp(input.action as "steam-start" | "steam-stop" | "retroarch-focus" | "retroarch-stop") }, { headers: { "Cache-Control": "no-store" } });
  } catch (error) { return NextResponse.json({ error: error instanceof GamingAppError ? error.message : "The application action failed." }, { status: 502 }); }
}
