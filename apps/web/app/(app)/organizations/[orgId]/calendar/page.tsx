"use client";

import Link from "next/link";

import { useOrg } from "@/components/org-shell";
import { PageHeader } from "@/components/page-header";
import { EmptyState, ErrorState, LoadingRows } from "@/components/states";
import { Badge } from "@/components/ui/badge";
import { can, useResource, type CalendarItem } from "@/lib/api";

function when(value: string | null) {
  return value ? new Date(value).toLocaleString() : null;
}

export default function CalendarPage() {
  const organization = useOrg();
  const base = `/organizations/${organization.id}`;
  const { data, error, loading, reload } = useResource<{ items: CalendarItem[] }>(`${base}/calendar`);
  const items = data?.items ?? [];
  const scheduled = items
    .filter((item) => item.scheduled_for && !item.published_at)
    .sort((a, b) => a.scheduled_for!.localeCompare(b.scheduled_for!));
  const ready = items.filter((item) => !item.scheduled_for && !item.published_at);
  const published = items.filter((item) => item.published_at);

  function group(title: string, rows: CalendarItem[], empty: string) {
    return (
      <section className="space-y-2">
        <h2 className="text-sm font-medium">
          {title} ({rows.length})
        </h2>
        {rows.length === 0 ? (
          <p className="rounded-lg border border-dashed p-4 text-sm text-muted-foreground">{empty}</p>
        ) : (
          <ul className="divide-y rounded-xl border bg-card">
            {rows.map((item) => (
              <li key={item.content_id}>
                <Link
                  href={`${base}/content-studio/${item.content_id}`}
                  className="flex flex-wrap items-center justify-between gap-3 p-4 text-sm first:rounded-t-xl last:rounded-b-xl hover:bg-muted/50"
                >
                  <span className="min-w-0">
                    <span className="block truncate font-medium">{item.title}</span>
                    <span className="block truncate text-muted-foreground">
                      {item.brand_name} · {item.platform} · version {item.version}
                    </span>
                  </span>
                  <span className="flex flex-wrap items-center gap-2 text-muted-foreground">
                    {when(item.published_at) ?? when(item.scheduled_for)}
                    {item.kind === "ad" ? <Badge variant="outline">Ad</Badge> : null}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    );
  }

  return (
    <>
      <PageHeader
        title="Publishing Calendar"
        description="Only content approved in its exact version appears here. Post it yourself and record the link, until platform accounts are connected."
      />
      {!can.viewCampaigns(organization.role) ? (
        <EmptyState title="Nothing assigned">Your role cannot view the calendar yet.</EmptyState>
      ) : loading ? (
        <LoadingRows />
      ) : error ? (
        <ErrorState message={error.message} onRetry={reload} />
      ) : (
        <div className="space-y-6">
          {group("Scheduled", scheduled, "Nothing scheduled.")}
          {group("Approved, not scheduled", ready, "No approved content is waiting.")}
          {group("Published", published, "Nothing published yet.")}
        </div>
      )}
    </>
  );
}
