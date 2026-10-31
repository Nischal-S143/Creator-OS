"use client";

import { useRef, useState, type ChangeEvent } from "react";
import { toast } from "sonner";

import { EmptyState, ErrorState, LoadingRows } from "@/components/states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  ApiError,
  api,
  can,
  uploadFile,
  useResource,
  type BrandDocument,
  type BrandProfile,
  type Role,
} from "@/lib/api";

function message(caught: unknown, fallback: string) {
  return caught instanceof ApiError ? caught.message : fallback;
}

const STATUS_LABELS: Record<BrandProfile["status"], string> = {
  proposed: "Waiting for approval",
  approved: "Approved",
  rejected: "Rejected",
  superseded: "Replaced",
};

function ProfileCard({
  profile,
  base,
  role,
  onChanged,
}: {
  profile: BrandProfile;
  base: string;
  role: Role;
  onChanged: () => void;
}) {
  const [busy, setBusy] = useState(false);

  async function act(path: string, body: unknown, success: string) {
    setBusy(true);
    try {
      const updated = await api<BrandProfile>(`${base}/profiles/${profile.id}/${path}`, {
        method: "POST",
        body,
      });
      if (updated.status === "approved" && updated.memory_status === "failed") {
        toast.warning("Approved and saved, but agent memory could not be updated. You can retry.");
      } else {
        toast.success(success);
      }
      onChanged();
    } catch (caught) {
      toast.error(message(caught, "Could not update this profile."));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-3 rounded-lg border p-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-medium">Version {profile.version}</span>
        <Badge variant={profile.status === "approved" ? "default" : "secondary"}>
          {STATUS_LABELS[profile.status]}
        </Badge>
        {profile.status === "approved" && profile.memory_status === "synced" ? (
          <Badge variant="outline">Saved to agent memory</Badge>
        ) : null}
      </div>
      <dl className="grid gap-3 text-sm sm:grid-cols-2">
        <div>
          <dt className="font-medium">Voice</dt>
          <dd className="text-muted-foreground">{profile.voice}</dd>
        </div>
        <div>
          <dt className="font-medium">Tone</dt>
          <dd className="text-muted-foreground">{profile.tone}</dd>
        </div>
        <div className="sm:col-span-2">
          <dt className="font-medium">Audience</dt>
          <dd className="text-muted-foreground">{profile.audience}</dd>
        </div>
        <div>
          <dt className="font-medium">Content pillars</dt>
          <dd className="text-muted-foreground">
            <ul className="list-inside list-disc">
              {profile.content_pillars.map((pillar) => (
                <li key={pillar}>{pillar}</li>
              ))}
            </ul>
          </dd>
        </div>
        <div>
          <dt className="font-medium">Restrictions</dt>
          <dd className="text-muted-foreground">
            {profile.restrictions.length === 0 ? (
              "None stated"
            ) : (
              <ul className="list-inside list-disc">
                {profile.restrictions.map((restriction) => (
                  <li key={restriction}>{restriction}</li>
                ))}
              </ul>
            )}
          </dd>
        </div>
      </dl>
      {can.approveProfile(role) && profile.status === "proposed" ? (
        <div className="flex flex-wrap gap-2">
          <Button
            size="sm"
            disabled={busy}
            onClick={() => act("decision", { approve: true }, "Profile approved")}
          >
            Approve profile
          </Button>
          <Button
            size="sm"
            variant="outline"
            disabled={busy}
            onClick={() => act("decision", { approve: false }, "Profile rejected")}
          >
            Reject
          </Button>
        </div>
      ) : null}
      {can.approveProfile(role) &&
      profile.status === "approved" &&
      profile.memory_status !== "synced" ? (
        <Button
          size="sm"
          variant="outline"
          disabled={busy}
          onClick={() => act("sync-memory", undefined, "Saved to agent memory")}
        >
          Retry agent memory
        </Button>
      ) : null}
    </div>
  );
}

export function BrandBrain({ base, role }: { base: string; role: Role }) {
  const documents = useResource<{ items: BrandDocument[] }>(`${base}/documents`);
  const profiles = useResource<{ items: BrandProfile[] }>(`${base}/profiles`);
  const input = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [extracting, setExtracting] = useState<string | null>(null);
  const editable = can.editBrand(role);

  async function onFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      await uploadFile(`${base}/documents`, file);
      toast.success(`Uploaded ${file.name}`);
      documents.reload();
    } catch (caught) {
      toast.error(message(caught, "Could not upload this file."));
    } finally {
      setUploading(false);
      event.target.value = "";
    }
  }

  async function extract(document: BrandDocument) {
    setExtracting(document.id);
    try {
      await api(`${base}/documents/${document.id}/extract-profile`, { method: "POST" });
      toast.success("Profile drafted. Review it below.");
      profiles.reload();
    } catch (caught) {
      toast.error(message(caught, "Could not draft a profile."));
    } finally {
      setExtracting(null);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Brand Brain</CardTitle>
        <CardDescription>
          Upload brand guidelines, review what AI extracts, and approve it. Campaigns use only approved
          profiles.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <section className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="text-sm font-medium">Brand documents</h3>
            {editable ? (
              <>
                <input
                  ref={input}
                  type="file"
                  accept=".pdf,.txt,.md"
                  className="sr-only"
                  aria-label="Brand document file"
                  onChange={onFile}
                />
                <Button
                  size="sm"
                  variant="outline"
                  disabled={uploading}
                  onClick={() => input.current?.click()}
                >
                  {uploading ? "Uploading…" : "Upload document"}
                </Button>
              </>
            ) : null}
          </div>
          {documents.loading ? <LoadingRows rows={1} /> : null}
          {documents.error ? (
            <ErrorState message={documents.error.message} onRetry={documents.reload} />
          ) : null}
          {documents.data?.items.length === 0 ? (
            <EmptyState title="No documents yet">PDF, TXT or Markdown, up to 10 MB.</EmptyState>
          ) : null}
          <ul className="space-y-2">
            {documents.data?.items.map((document) => (
              <li
                key={document.id}
                className="flex flex-wrap items-center justify-between gap-2 rounded-lg border p-3 text-sm"
              >
                <span className="min-w-0 truncate">{document.filename}</span>
                {editable ? (
                  <Button
                    size="sm"
                    disabled={extracting !== null}
                    onClick={() => extract(document)}
                  >
                    {extracting === document.id ? "Drafting…" : "Draft profile with AI"}
                  </Button>
                ) : null}
              </li>
            ))}
          </ul>
        </section>
        <section className="space-y-3">
          <h3 className="text-sm font-medium">Brand profiles</h3>
          {profiles.loading ? <LoadingRows rows={1} /> : null}
          {profiles.error ? (
            <ErrorState message={profiles.error.message} onRetry={profiles.reload} />
          ) : null}
          {profiles.data?.items.length === 0 ? (
            <EmptyState title="No profiles yet">Draft one from an uploaded document.</EmptyState>
          ) : null}
          {profiles.data?.items.map((profile) => (
            <ProfileCard
              key={profile.id}
              profile={profile}
              base={base}
              role={role}
              onChanged={profiles.reload}
            />
          ))}
        </section>
      </CardContent>
    </Card>
  );
}
