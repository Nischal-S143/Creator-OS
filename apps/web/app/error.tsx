"use client";

import { ErrorState } from "@/components/states";

export default function ErrorPage({ reset }: { error: Error; reset: () => void }) {
  return (
    <main className="mx-auto w-full max-w-lg p-8">
      <ErrorState message="Something went wrong on this page." onRetry={reset} />
    </main>
  );
}
