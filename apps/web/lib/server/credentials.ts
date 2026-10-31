import "server-only";

import { NextResponse } from "next/server";

import {
  SESSION_COOKIE,
  backendUrl,
  isSameOrigin,
  sessionCookieOptions,
} from "@/lib/server/session";

/** Exchanges credentials for a token and stores it where browser scripts cannot read it. */
export async function exchangeCredentials(
  request: Request,
  backendPath: string,
): Promise<NextResponse> {
  if (!isSameOrigin(request)) {
    return NextResponse.json({ detail: "forbidden" }, { status: 403 });
  }
  let upstream: Response;
  try {
    upstream = await fetch(backendUrl(backendPath), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: await request.text(),
      cache: "no-store",
    });
  } catch {
    return NextResponse.json(
      { detail: "The service is unavailable. Try again shortly." },
      { status: 503 },
    );
  }
  const body = await upstream.json().catch(() => ({}));
  if (!upstream.ok) {
    return NextResponse.json({ detail: body.detail }, { status: upstream.status });
  }
  const response = NextResponse.json({ ok: true }, { status: upstream.status });
  response.cookies.set(
    SESSION_COOKIE,
    body.access_token,
    sessionCookieOptions(body.expires_in),
  );
  return response;
}
