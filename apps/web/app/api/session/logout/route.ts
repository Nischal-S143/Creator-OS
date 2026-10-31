import { NextResponse } from "next/server";

import {
  SESSION_COOKIE,
  isSameOrigin,
  sessionCookieOptions,
} from "@/lib/server/session";

export async function POST(request: Request) {
  if (!isSameOrigin(request)) {
    return NextResponse.json({ detail: "forbidden" }, { status: 403 });
  }
  const response = NextResponse.json({ ok: true });
  response.cookies.set(SESSION_COOKIE, "", sessionCookieOptions(0));
  return response;
}
