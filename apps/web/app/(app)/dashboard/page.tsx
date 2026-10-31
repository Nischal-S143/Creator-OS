"use client";

import { ChevronRightIcon } from "lucide-react";
import Link from "next/link";
import { useState, type FormEvent } from "react";
import { toast } from "sonner";

import { signOut, useMe } from "@/components/app-shell";
import { Logo } from "@/components/logo";
import { EmptyState } from "@/components/states";
import { ThemeToggle } from "@/components/theme-toggle";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError, ROLE_LABELS, api, slugify, type Organization } from "@/lib/api";

export default function DashboardPage() {
  const { me, reload } = useMe();
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const slug = slugify(name);

  async function create(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    try {
      await api<Organization>("/organizations", { method: "POST", body: { name, slug } });
      toast.success(`Created ${name}`);
      setName("");
      reload();
    } catch (caught) {
      toast.error(caught instanceof ApiError ? caught.message : "Could not create the agency.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="min-h-screen">
      <header className="border-b bg-background">
        <div className="mx-auto flex h-14 max-w-3xl items-center justify-between gap-3 px-4">
          <Logo />
          <div className="flex min-w-0 items-center gap-3">
            <span className="hidden truncate text-sm text-muted-foreground sm:inline">{me.email}</span>
            <ThemeToggle />
            <Button variant="outline" size="sm" onClick={signOut}>
              Sign out
            </Button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-3xl space-y-8 px-4 py-8">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Your agencies</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Each agency has its own clients, members and data.
          </p>
        </div>

        {me.organizations.length === 0 ? (
          <EmptyState title="No agencies yet">Create your first agency below to get started.</EmptyState>
        ) : (
          <ul className="divide-y rounded-xl border bg-card">
            {me.organizations.map((organization) => (
              <li key={organization.id}>
                <Link
                  href={`/organizations/${organization.id}`}
                  className="flex items-center justify-between gap-3 p-4 outline-none first:rounded-t-xl last:rounded-b-xl hover:bg-muted/50 focus-visible:ring-2 focus-visible:ring-ring"
                >
                  <span className="min-w-0">
                    <span className="block truncate font-medium">{organization.name}</span>
                    <span className="block truncate text-sm text-muted-foreground">
                      {organization.slug}
                    </span>
                  </span>
                  <span className="flex shrink-0 items-center gap-2">
                    <Badge variant="secondary">{ROLE_LABELS[organization.role]}</Badge>
                    <ChevronRightIcon className="size-4 text-muted-foreground" aria-hidden="true" />
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}

        <Card>
          <CardHeader>
            <CardTitle>Create an agency</CardTitle>
            <CardDescription>You will be its owner.</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={create} className="flex flex-col gap-3 sm:flex-row sm:items-start">
              <div className="flex-1 space-y-2">
                <Label htmlFor="agency-name">Agency name</Label>
                <Input
                  id="agency-name"
                  required
                  maxLength={200}
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                />
                {slug ? <p className="text-xs text-muted-foreground">Address: {slug}</p> : null}
              </div>
              <Button type="submit" disabled={busy || slug.length < 2} className="sm:mt-[1.375rem]">
                {busy ? "Creating…" : "Create agency"}
              </Button>
            </form>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
