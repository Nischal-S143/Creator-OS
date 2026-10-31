"use client";

import { signOut, useMe } from "@/components/app-shell";
import { useOrg } from "@/components/org-shell";
import { PageHeader } from "@/components/page-header";
import { ThemeToggle } from "@/components/theme-toggle";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ROLE_LABELS } from "@/lib/api";

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-2 py-3 text-sm first:pt-0 last:pb-0">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="min-w-0 truncate font-medium">{children}</dd>
    </div>
  );
}

export default function SettingsPage() {
  const organization = useOrg();
  const { me } = useMe();
  return (
    <>
      <PageHeader title="Settings" description="Your agency, account and display preferences." />
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Agency</CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="divide-y">
              <Row label="Name">{organization.name}</Row>
              <Row label="Address">{organization.slug}</Row>
              <Row label="Plan">
                <span className="capitalize">{organization.plan}</span>
              </Row>
              <Row label="Your role">{ROLE_LABELS[organization.role]}</Row>
            </dl>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Account</CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="divide-y">
              <Row label="Email">{me.email}</Row>
              <Row label="Theme">
                <ThemeToggle />
              </Row>
            </dl>
            <Button variant="outline" size="sm" className="mt-4" onClick={signOut}>
              Sign out of this device
            </Button>
          </CardContent>
        </Card>
      </div>
    </>
  );
}
