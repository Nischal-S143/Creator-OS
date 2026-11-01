import { NextResponse, type NextRequest } from "next/server";

const SESSION_COOKIE = "creatoros_session";
// The marketing home page renders for signed-out visitors, same as the auth pages.
const REDIRECTS_SIGNED_IN_HOME = new Set(["/", "/sign-in", "/sign-up"]);

export function proxy(request: NextRequest) {
  const signedIn = request.cookies.has(SESSION_COOKIE);
  const { pathname } = request.nextUrl;
  if (REDIRECTS_SIGNED_IN_HOME.has(pathname)) {
    return signedIn
      ? NextResponse.redirect(new URL("/dashboard", request.url))
      : NextResponse.next();
  }
  if (!signedIn) {
    return NextResponse.redirect(new URL("/sign-in", request.url));
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!api|_next|favicon\\.ico|icon\\.svg).*)"],
};
