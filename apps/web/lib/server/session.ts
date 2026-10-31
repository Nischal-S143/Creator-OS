import "server-only";

export const SESSION_COOKIE = "creatoros_session";

export function backendUrl(path: string): string {
  const base = process.env.API_URL ?? "http://127.0.0.1:8000";
  return `${base}${path}`;
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
