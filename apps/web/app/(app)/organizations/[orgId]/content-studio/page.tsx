"use client";

import Link from "next/link";

import { useOrg } from "@/components/org-shell";
import { PageHeader } from "@/components/page-header";
import { EmptyState, ErrorState, LoadingRows } from "@/components/states";
import { StatusBadge } from "@/components/status-badge";
import { Badge } from "@/components/ui/badge";
import { can, useResource, type ContentRow } from "@/lib/api";

export default function ContentStudioPage() {
  const organization = useOrg();
  const base = `/organizations/${organization.id}`;
  const allowed = can.viewCampaigns(organization.role);
  const { data, error, loading, reload } = useResource<{ items: ContentRow[] }>(`${base}/content`);

  return (
    <>
      <PageHeader title="Content Studio" description="Scripts and ads, with every version kept." />
      {!allowed ? (
        <EmptyState title="Nothing assigned">Your role cannot view content yet.</EmptyState>
      ) : loading ? (
        <LoadingRows />
      ) : error ? (
        <ErrorState message={error.message} onRetry={reload} />
      ) : data?.items.length === 0 ? (
        <EmptyState title="No content yet">
          Open a campaign, generate ideas, and choose &quot;Create content&quot; on one.
        </EmptyState>
      ) : (
        <ul className="divide-y rounded-xl border bg-card">
          {data?.items.map((item) => (
            <li key={item.id}>
              <Link
                href={`${base}/content-studio/${item.id}`}
                className="flex flex-wrap items-center justify-between gap-3 p-4 text-sm first:rounded-t-xl last:rounded-b-xl hover:bg-muted/50"
              >
                <span className="min-w-0">
                  <span className="block truncate font-medium">{item.title}</span>
                  <span className="block truncate text-muted-foreground">
                    {item.brand_name} · {item.platform} · version {item.current_version}
                  </span>
                </span>
                <span className="flex items-center gap-2">
                  {item.kind === "ad" ? <Badge variant="outline">Ad</Badge> : null}
                  <StatusBadge status={item.status} />
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
