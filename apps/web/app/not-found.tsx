import Link from "next/link";

export default function NotFound() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-3 p-8 text-center">
      <h1 className="text-2xl font-semibold tracking-tight">Page not found</h1>
      <p className="text-sm text-muted-foreground">This page does not exist or has moved.</p>
      <Link href="/dashboard" className="text-sm underline underline-offset-4">
        Go to your agencies
      </Link>
    </main>
  );
}
