"use client";

import { createContext, useContext } from "react";

import { ErrorState } from "@/components/states";
import { Skeleton } from "@/components/ui/skeleton";
import { request, useResource, type Me } from "@/lib/api";

const MeContext = createContext<{ me: Me; reload: () => void } | null>(null);

export function useMe() {
  const value = useContext(MeContext);
  if (!value) throw new Error("useMe must be used inside AppShell");
  return value;
}

export async function signOut() {
  await request("/api/session/logout", { method: "POST" });
  window.location.assign("/sign-in");
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const { data, error, loading, reload } = useResource<Me>("/me");

  if (loading) {
    return (
      <div className="flex min-h-screen" role="status" aria-label="Loading">
        <Skeleton className="hidden w-72 rounded-none lg:block" />
        <div className="flex-1 space-y-4 p-8">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-32 w-full" />
        </div>
      </div>
    );
  }
  if (error || !data) {
    return (
      <main className="mx-auto w-full max-w-lg p-8">
        <ErrorState message={error?.message ?? "Something went wrong."} onRetry={reload} />
      </main>
    );
  }
  return <MeContext.Provider value={{ me: data, reload }}>{children}</MeContext.Provider>;
}
