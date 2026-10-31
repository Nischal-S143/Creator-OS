"use client";

import Link from "next/link";

import { useOrg } from "@/components/org-shell";
import { PageHeader } from "@/components/page-header";
import { EmptyState, ErrorState, LoadingRows } from "@/components/states";
import { StatusBadge } from "@/components/status-badge";
import { can, useResource, type GuardianRow } from "@/lib/api";

export default function BrandGuardianPage() {
  const organization = useOrg();
  const base = `/organizations/${organization.id}`;
  const { data, error, loading, reload } = useResource<{ items: GuardianRow[] }>(`${base}/guardian-reviews`);

  return (
    <>
      <PageHeader
        title="Brand Guardian"
        description="Independent AI review of voice, restrictions, claims and platform policy. Visual and licensing checks need generated media first."
      />
      {!can.viewCampaigns(organization.role) ? (
        <EmptyState title="Nothing assigned">Your role cannot view reviews yet.</EmptyState>
      ) : loading ? (
        <LoadingRows />
      ) : error ? (
        <ErrorState message={error.message} onRetry={reload} />
      ) : data?.items.length === 0 ? (
        <EmptyState title="No reviews yet">Every new content version gets reviewed here.</EmptyState>
      ) : (
        <ul className="divide-y rounded-xl border bg-card">
          {data?.items.map((review) => (
            <li key={review.id}>
              <Link
                href={`${base}/content-studio/${review.content_id}`}
                className="flex flex-wrap items-center justify-between gap-3 p-4 text-sm first:rounded-t-xl last:rounded-b-xl hover:bg-muted/50"
              >
                <span className="min-w-0">
                  <span className="block truncate font-medium">{review.title}</span>
                  <span className="block truncate text-muted-foreground">
                    {review.brand_name} · version {review.content_version} · {review.findings}{" "}
                    {review.findings === 1 ? "finding" : "findings"}
                  </span>
                </span>
                <StatusBadge status={review.status} />
              </Link>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
