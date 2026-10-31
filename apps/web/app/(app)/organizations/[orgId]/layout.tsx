"use client";

import Link from "next/link";
import { use } from "react";

import { useMe } from "@/components/app-shell";
import { OrgShell } from "@/components/org-shell";
import { ErrorState } from "@/components/states";

export default function OrganizationLayout({
  params,
  children,
}: {
  params: Promise<{ orgId: string }>;
  children: React.ReactNode;
}) {
  const { orgId } = use(params);
  const { me } = useMe();
  const organization = me.organizations.find((item) => item.id === orgId);
  if (!organization) {
    return (
      <main className="mx-auto w-full max-w-lg space-y-4 p-8">
        <ErrorState message="This agency does not exist or you do not have access to it." />
        <Link href="/dashboard" className="text-sm underline underline-offset-4">
          Go to your agencies
        </Link>
      </main>
    );
  }
  return <OrgShell organization={organization}>{children}</OrgShell>;
}
