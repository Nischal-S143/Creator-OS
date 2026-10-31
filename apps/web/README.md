# CreatorOS web

Next.js, TypeScript, Tailwind CSS and shadcn/ui. Setup is in the root [README](../../README.md).

The browser never sees API tokens: `app/api/session` stores them in an httpOnly cookie, and `app/api/backend` forwards allowed requests to the API.
