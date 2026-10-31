"use client";

import Link from "next/link";

import { useOrg } from "@/components/org-shell";
import { PageHeader } from "@/components/page-header";
import { EmptyState, ErrorState, LoadingRows } from "@/components/states";
import { StatusBadge } from "@/components/status-badge";
import { can, useResource, type PendingApproval } from "@/lib/api";

export default function ApprovalCenterPage() {
  const organization = useOrg();
  const base = `/organizations/${organization.id}`;
  const { data, error, loading, reload } = useResource<{ items: PendingApproval[] }>(`${base}/approvals`);

  return (
    <>
      <PageHeader
        title="Approval Center"
        description="Content waiting for a person. Approval applies to one exact version."
      />
      {!can.viewCampaigns(organization.role) ? (
        <EmptyState title="Nothing assigned">Your role cannot view approvals yet.</EmptyState>
      ) : loading ? (
        <LoadingRows />
      ) : error ? (
        <ErrorState message={error.message} onRetry={reload} />
      ) : data?.items.length === 0 ? (
        <EmptyState title="Nothing waiting">Content appears here after Brand Guardian reviews it.</EmptyState>
      ) : (
        <ul className="divide-y rounded-xl border bg-card">
          {data?.items.map((item) => (
            <li key={item.approval_id}>
              <Link
                href={`${base}/content-studio/${item.content.id}`}
                className="flex flex-wrap items-center justify-between gap-3 p-4 text-sm first:rounded-t-xl last:rounded-b-xl hover:bg-muted/50"
              >
                <span className="min-w-0">
                  <span className="block truncate font-medium">{item.content.title}</span>
                  <span className="block truncate text-muted-foreground">
                    {item.brand_name} · version {item.content_version}
                  </span>
                </span>
                {item.guardian_status ? <StatusBadge status={item.guardian_status} /> : null}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
