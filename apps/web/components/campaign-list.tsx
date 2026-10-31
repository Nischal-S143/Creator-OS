"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";
import { toast } from "sonner";

import { EmptyState, ErrorState, LoadingRows } from "@/components/states";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError, api, can, useResource, type Campaign, type Role } from "@/lib/api";

export function CampaignList({
  base,
  webBase,
  role,
}: {
  base: string;
  webBase: string;
  role: Role;
}) {
  const { data, error, loading, reload } = useResource<{ items: Campaign[] }>(`${base}/campaigns`);
  const [name, setName] = useState("");
  const [objective, setObjective] = useState("");
  const [busy, setBusy] = useState(false);

  async function create(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    try {
      await api<Campaign>(`${base}/campaigns`, { method: "POST", body: { name, objective } });
      toast.success(`Created ${name}`);
      setName("");
      setObjective("");
      reload();
    } catch (caught) {
      toast.error(caught instanceof ApiError ? caught.message : "Could not create the campaign.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Campaigns</CardTitle>
        <CardDescription>Each campaign gets AI ideas based on the approved brand profile.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {loading ? <LoadingRows rows={1} /> : null}
        {error ? <ErrorState message={error.message} onRetry={reload} /> : null}
        {data?.items.length === 0 ? (
          <EmptyState title="No campaigns yet">Campaigns for this client appear here.</EmptyState>
        ) : null}
        <ul className="space-y-2">
          {data?.items.map((campaign) => (
            <li key={campaign.id}>
              <Link
                href={`${webBase}/campaigns/${campaign.id}`}
                className="block rounded-lg border p-3 text-sm transition-colors hover:bg-muted/50"
              >
                <span className="font-medium">{campaign.name}</span>
                <span className="block truncate text-muted-foreground">{campaign.objective}</span>
              </Link>
            </li>
          ))}
        </ul>
        {can.editCampaign(role) ? (
          <form onSubmit={create} className="grid gap-4 border-t pt-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="campaign-name">Campaign name</Label>
              <Input
                id="campaign-name"
                required
                maxLength={200}
                value={name}
                onChange={(event) => setName(event.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="campaign-objective">Objective</Label>
              <Input
                id="campaign-objective"
                required
                minLength={3}
                maxLength={2000}
                value={objective}
                onChange={(event) => setObjective(event.target.value)}
              />
            </div>
            <div className="sm:col-span-2">
              <Button type="submit" disabled={busy}>
                {busy ? "Creating…" : "Create campaign"}
              </Button>
            </div>
          </form>
        ) : null}
      </CardContent>
    </Card>
  );
}
