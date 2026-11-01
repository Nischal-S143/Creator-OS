import "server-only";

export const SESSION_COOKIE = "creatoros_session";

/**
 * Base URL of the API service. On Vercel the `api` service binding injects it into
 * `API_URL` at request time, so it is read per call and never at build time or in
 * `proxy.ts`, where bindings do not resolve. The default is local development.
 */
export function backendUrl(path: string): string {
  const base = process.env.API_URL ?? "http://127.0.0.1:8000";
  // Joining instead of concatenating keeps a base that ends in "/" from doubling the slash.
  return new URL(path, base).toString();
}

export function sessionCookieOptions(maxAge: number) {
  return {
    httpOnly: true,
    sameSite: "lax" as const,
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge,
  };
}

/** Refuses state-changing requests sent by other websites. */
export function isSameOrigin(request: Request): boolean {
  const origin = request.headers.get("origin");
  if (!origin) return false;
  const host = request.headers.get("x-forwarded-host") ?? request.headers.get("host");
  try {
    return new URL(origin).host === host;
  } catch {
    return false;
  }
}
