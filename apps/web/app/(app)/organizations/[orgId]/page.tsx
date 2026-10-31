"use client";

import { CheckCircle2Icon, CircleIcon } from "lucide-react";
import Link from "next/link";

import { useOrg } from "@/components/org-shell";
import { PageHeader } from "@/components/page-header";
import { ErrorState, LoadingRows } from "@/components/states";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ROLE_LABELS, can, useResource, type Brand, type Member, type Page } from "@/lib/api";

function Stat({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <Card size="sm">
      <CardContent>
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className="mt-1 text-2xl font-semibold tracking-tight capitalize">{value}</p>
      </CardContent>
    </Card>
  );
}

function Step({ done, href, children }: { done: boolean; href: string; children: React.ReactNode }) {
  return (
    <li>
      <Link
        href={href}
        className="flex items-center gap-2 rounded-md p-2 text-sm hover:bg-muted"
      >
        {done ? (
          <CheckCircle2Icon className="size-4 shrink-0 text-primary" aria-label="Done" />
        ) : (
          <CircleIcon className="size-4 shrink-0 text-muted-foreground" aria-label="To do" />
        )}
        <span className={done ? "text-muted-foreground" : undefined}>{children}</span>
      </Link>
    </li>
  );
}

function Clients({ base }: { base: string }) {
  const { data, error, loading, reload } = useResource<Page<Brand>>(
    `${base}/brands?limit=5`,
  );
  if (loading) return <LoadingRows rows={2} />;
  if (error) return <ErrorState message={error.message} onRetry={reload} />;
  if (!data) return null;
  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <Stat label="Clients" value={data.total} />
        <Members base={base} />
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Get started</CardTitle>
            <CardDescription>The steps that make AI campaigns possible.</CardDescription>
          </CardHeader>
          <CardContent>
            <ul>
              <Step done={data.total > 0} href={`${base}/clients`}>
                Add your first client
              </Step>
              <Step done={false} href={`${base}/brand-brain`}>
                Upload brand guidelines and approve a profile
              </Step>
              <Step done={false} href={`${base}/campaigns`}>
                Create a campaign and generate ideas
              </Step>
            </ul>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Recent clients</CardTitle>
          </CardHeader>
          <CardContent>
            {data.items.length === 0 ? (
              <p className="text-sm text-muted-foreground">No clients yet.</p>
            ) : (
              <ul>
                {data.items.map((brand) => (
                  <li key={brand.id}>
                    <Link
                      href={`${base}/brands/${brand.id}`}
                      className="flex justify-between gap-2 rounded-md p-2 text-sm hover:bg-muted"
                    >
                      <span className="truncate font-medium">{brand.name}</span>
                      <span className="truncate text-muted-foreground">{brand.industry}</span>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function Members({ base }: { base: string }) {
  const organization = useOrg();
  if (!can.viewMembers(organization.role)) return <Stat label="Your role" value={ROLE_LABELS[organization.role]} />;
  return <MemberCount base={base} />;
}

function MemberCount({ base }: { base: string }) {
  const { data, error } = useResource<Page<Member>>(`${base}/members?limit=100`);
  if (error) return <Stat label="Active members" value="–" />;
  if (!data) return <Skeleton className="h-20" />;
  return (
    <Stat label="Active members" value={data.items.filter((member) => member.status === "active").length} />
  );
}

export default function OverviewPage() {
  const organization = useOrg();
  const base = `/organizations/${organization.id}`;
  return (
    <>
      <PageHeader title={organization.name} description={`You are signed in as ${ROLE_LABELS[organization.role].toLowerCase()}.`} />
      {can.viewBrands(organization.role) ? (
        <Clients base={base} />
      ) : (
        <Card>
          <CardHeader>
            <CardTitle>Nothing assigned yet</CardTitle>
            <CardDescription>
              Client approvers see content here once brands are assigned to them.
            </CardDescription>
          </CardHeader>
        </Card>
      )}
    </>
  );
}
