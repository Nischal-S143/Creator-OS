"use client";

import Link from "next/link";

import { useOrg } from "@/components/org-shell";
import { PageHeader } from "@/components/page-header";
import { EmptyState, ErrorState, LoadingRows } from "@/components/states";
import { Badge } from "@/components/ui/badge";
import { can, useResource, type CalendarItem } from "@/lib/api";

export default function AnalyticsPage() {
  const organization = useOrg();
  const base = `/organizations/${organization.id}`;
  const { data, error, loading, reload } = useResource<{ items: CalendarItem[] }>(`${base}/calendar`);
  const published = (data?.items ?? []).filter((item) => item.published_at);

  return (
    <>
      <PageHeader
        title="Analytics"
        description="Enter each post's results at 48 hours, 7 days and 30 days. Software compares them with the brand's other posts, and AI suggests why. You approve what becomes a lesson."
      />
      {!can.viewCampaigns(organization.role) ? (
        <EmptyState title="Nothing assigned">Your role cannot view analytics yet.</EmptyState>
      ) : loading ? (
        <LoadingRows />
      ) : error ? (
        <ErrorState message={error.message} onRetry={reload} />
      ) : published.length === 0 ? (
        <EmptyState title="No published posts yet">
          Approve content, then record it as published in Content Studio.
        </EmptyState>
      ) : (
        <ul className="divide-y rounded-xl border bg-card">
          {published.map((item) => (
            <li key={item.content_id}>
              <Link
                href={`${base}/content-studio/${item.content_id}`}
                className="flex flex-wrap items-center justify-between gap-3 p-4 text-sm first:rounded-t-xl last:rounded-b-xl hover:bg-muted/50"
              >
                <span className="min-w-0">
                  <span className="block truncate font-medium">{item.title}</span>
                  <span className="block truncate text-muted-foreground">
                    {item.brand_name} · {item.platform}
                  </span>
                </span>
                <span className="flex flex-wrap gap-1">
                  {["48h", "7d", "30d"].map((window) => (
                    <Badge key={window} variant={item.windows_reported.includes(window) ? "default" : "outline"}>
                      {window}
                    </Badge>
                  ))}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
