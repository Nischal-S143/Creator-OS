import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { SESSION_COOKIE, backendUrl, isSameOrigin } from "@/lib/server/session";

const ALLOWED_ROOTS = new Set(["me", "organizations"]);

type Context = { params: Promise<{ path: string[] }> };

async function forward(request: Request, context: Context): Promise<NextResponse> {
  const { path } = await context.params;
  // Only these API areas are reachable, so the internal AI test route is not exposed through the browser.
  if (!ALLOWED_ROOTS.has(path[0]) || path.some((part) => part === "." || part === "..")) {
    return NextResponse.json({ detail: "not found" }, { status: 404 });
  }
  if (request.method !== "GET" && !isSameOrigin(request)) {
    return NextResponse.json({ detail: "forbidden" }, { status: 403 });
  }
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) {
    return NextResponse.json({ detail: "not authenticated" }, { status: 401 });
  }
  const search = new URL(request.url).search;
  const target = `/api/v1/${path.map(encodeURIComponent).join("/")}${search}`;
  let upstream: Response;
  try {
    upstream = await fetch(backendUrl(target), {
      method: request.method,
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": request.headers.get("content-type") ?? "application/json",
      },
      body: request.method === "GET" ? undefined : await request.arrayBuffer(),
      cache: "no-store",
    });
  } catch {
    return NextResponse.json(
      { detail: "The service is unavailable. Try again shortly." },
      { status: 503 },
    );
  }
  const contentType = upstream.headers.get("content-type") ?? "";
  if (!contentType.startsWith("application/json")) {
    // Generated images and video: stream the bytes through as-is, with no JSON parsing.
    return new NextResponse(upstream.body, {
      status: upstream.status,
      headers: { "content-type": contentType || "application/octet-stream" },
    });
  }
  const body = await upstream.json().catch(() => ({}));
  return NextResponse.json(body, { status: upstream.status });
}

export const GET = forward;
export const POST = forward;
export const PATCH = forward;
export const DELETE = forward;
