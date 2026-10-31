"use client";

import { ChevronRightIcon } from "lucide-react";
import Link from "next/link";

import { useOrg } from "@/components/org-shell";
import { EmptyState, ErrorState, LoadingRows } from "@/components/states";
import { useResource, type Brand, type Page } from "@/lib/api";

/** Brand Brain and Campaign Studio belong to one client, so these pages start by choosing one. */
export function ClientPicker({ tab }: { tab: "brain" | "campaigns" }) {
  const organization = useOrg();
  const base = `/organizations/${organization.id}`;
  const { data, error, loading, reload } = useResource<Page<Brand>>(`${base}/brands?limit=100`);

  if (loading) return <LoadingRows />;
  if (error) return <ErrorState message={error.message} onRetry={reload} />;
  if (!data || data.items.length === 0) {
    return (
      <EmptyState title="No clients yet">
        <Link href={`${base}/clients`} className="underline underline-offset-4">
          Add a client
        </Link>{" "}
        to get started.
      </EmptyState>
    );
  }
  return (
    <ul className="divide-y rounded-xl border bg-card">
      {data.items.map((brand) => (
        <li key={brand.id}>
          <Link
            href={`${base}/brands/${brand.id}?tab=${tab}`}
            className="flex items-center justify-between gap-3 p-4 text-sm first:rounded-t-xl last:rounded-b-xl hover:bg-muted/50"
          >
            <span className="min-w-0">
              <span className="block truncate font-medium">{brand.name}</span>
              <span className="block truncate text-muted-foreground">
                {brand.industry ?? "No industry set"}
              </span>
            </span>
            <ChevronRightIcon className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
          </Link>
        </li>
      ))}
    </ul>
  );
}
