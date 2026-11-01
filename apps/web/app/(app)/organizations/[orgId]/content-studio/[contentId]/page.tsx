"use client";

import { use, useState, type FormEvent } from "react";
import { toast } from "sonner";

import { useOrg } from "@/components/org-shell";
import { PageHeader } from "@/components/page-header";
import { PublishAndResults } from "@/components/publish-and-results";
import { ErrorState, LoadingRows } from "@/components/states";
import { StatusBadge } from "@/components/status-badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  ApiError,
  api,
  can,
  useResource,
  type CalendarItem,
  type ContentDetail,
  type ContentVersion,
  type MediaItem,
} from "@/lib/api";

const textareaClass =
  "w-full rounded-lg border border-input bg-transparent px-2.5 py-1.5 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring";

function failure(caught: unknown, fallback: string) {
  return caught instanceof ApiError ? caught.message : fallback;
}

function EditForm({
  version,
  busy,
  onSave,
  onCancel,
}: {
  version: ContentVersion;
  busy: boolean;
  onSave: (body: object) => void;
  onCancel: () => void;
}) {
  const [hook, setHook] = useState(version.hook);
  const [script, setScript] = useState(version.script);
  const [caption, setCaption] = useState(version.caption);
  const [cta, setCta] = useState(version.cta);

  function submit(event: FormEvent) {
    event.preventDefault();
    onSave({ hook, script, caption, cta, hashtags: version.hashtags });
  }

  return (
    <form onSubmit={submit} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="edit-hook">Hook</Label>
        <Input id="edit-hook" required value={hook} onChange={(e) => setHook(e.target.value)} />
      </div>
      <div className="space-y-2">
        <Label htmlFor="edit-script">Script</Label>
        <textarea
          id="edit-script"
          required
          rows={8}
          className={textareaClass}
          value={script}
          onChange={(e) => setScript(e.target.value)}
        />
      </div>
      <div className="space-y-2">
        <Label htmlFor="edit-caption">Caption</Label>
        <textarea
          id="edit-caption"
          required
          rows={3}
          className={textareaClass}
          value={caption}
          onChange={(e) => setCaption(e.target.value)}
        />
      </div>
      <div className="space-y-2">
        <Label htmlFor="edit-cta">Call to action</Label>
        <Input id="edit-cta" required value={cta} onChange={(e) => setCta(e.target.value)} />
      </div>
      <p className="text-xs text-muted-foreground">
        Saving creates a new version. It goes back through Brand Guardian and needs new approval.
      </p>
      <div className="flex gap-2">
        <Button type="submit" disabled={busy}>
          {busy ? "Saving and reviewing…" : "Save new version"}
        </Button>
        <Button type="button" variant="outline" onClick={onCancel} disabled={busy}>
          Cancel
        </Button>
      </div>
    </form>
  );
}

function MediaButton({
  label,
  busy,
  disabled,
  onClick,
}: {
  label: string;
  busy: boolean;
  disabled: boolean;
  onClick: () => void;
}) {
  return (
    <Button size="sm" variant="outline" disabled={disabled || busy} onClick={onClick}>
      {busy ? "Generating…" : label}
    </Button>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="text-xs font-medium text-muted-foreground">{label}</p>
      <div className="mt-1 whitespace-pre-wrap text-sm">{children}</div>
    </div>
  );
}

export default function ContentDetailPage({ params }: { params: Promise<{ contentId: string }> }) {
  const { contentId } = use(params);
  const organization = useOrg();
  const base = `/organizations/${organization.id}`;
  const path = `${base}/content/${contentId}`;
  const [selected, setSelected] = useState<number | null>(null);
  const query = selected ? `?version=${selected}` : "";
  const { data, error, loading, reload } = useResource<ContentDetail>(`${path}${query}`);
  const [editing, setEditing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState("");
  const [generatingScene, setGeneratingScene] = useState<number | null>(null);
  const [generatingVideo, setGeneratingVideo] = useState(false);
  const calendar = useResource<{ items: CalendarItem[] }>(`${base}/calendar`);

  function mediaSrc(item: MediaItem): string {
    return `/api/backend${item.url}`;
  }

  async function generateImage(sceneIndex: number) {
    setGeneratingScene(sceneIndex);
    try {
      await api(`${path}/media/image`, { method: "POST", body: { scene_index: sceneIndex } });
      toast.success(`Scene ${sceneIndex + 1} image ready`);
      reload();
    } catch (caught) {
      toast.error(failure(caught, "Could not generate this image."));
    } finally {
      setGeneratingScene(null);
    }
  }

  async function generateVideo() {
    setGeneratingVideo(true);
    try {
      await api(`${path}/media/video`, { method: "POST" });
      toast.success("Video ready");
      reload();
    } catch (caught) {
      toast.error(failure(caught, "Could not generate a video."));
    } finally {
      setGeneratingVideo(false);
    }
  }

  async function run(action: () => Promise<unknown>, success: string, fallback: string) {
    setBusy(true);
    try {
      await action();
      toast.success(success);
      setEditing(false);
      setFeedback("");
      setSelected(null);
      reload();
    } catch (caught) {
      toast.error(failure(caught, fallback));
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <LoadingRows />;
  if (error) return <ErrorState message={error.message} onRetry={reload} />;
  if (!data) return null;

  const version = data.version;
  const viewingCurrent = version?.version === data.current_version;
  const canEdit = can.editCampaign(organization.role);
  const canApprove = can.approveContent(organization.role);
  const pending = data.approvals.find(
    (approval) => approval.decision === "pending" && approval.content_version === data.current_version,
  );
  const review = data.reviews.find((item) => item.content_version === version?.version);
  const research = version?.research;

  return (
    <>
      <PageHeader
        title={data.title}
        description={`${data.platform} · ${data.kind === "ad" ? "Ad" : "Organic post"}`}
        back={{ href: `${base}/content-studio`, label: "All content" }}
        actions={<StatusBadge status={data.status} />}
      />

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="space-y-4 lg:col-span-2">
          <Card>
            <CardHeader>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <CardTitle>
                  Version {version?.version ?? "–"}
                  {version ? (
                    <span className="ml-2 font-normal text-muted-foreground">
                      {version.source === "human" ? "edited by a person" : "written by AI"}
                    </span>
                  ) : null}
                </CardTitle>
                {data.versions.length > 1 ? (
                  <select
                    aria-label="Version"
                    value={version?.version}
                    onChange={(event) => setSelected(Number(event.target.value))}
                    className="h-8 rounded-lg border border-input bg-background px-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    {data.versions.map((number) => (
                      <option key={number} value={number}>
                        Version {number}
                      </option>
                    ))}
                  </select>
                ) : null}
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {!version ? (
                <p className="text-sm text-muted-foreground">No version was produced.</p>
              ) : editing ? (
                <EditForm
                  version={version}
                  busy={busy}
                  onCancel={() => setEditing(false)}
                  onSave={(body) =>
                    run(
                      () => api(`${path}/edit`, { method: "POST", body }),
                      "New version saved and reviewed",
                      "Could not save.",
                    )
                  }
                />
              ) : (
                <>
                  <Field label="Hook">{version.hook}</Field>
                  <Field label="Script">{version.script}</Field>
                  <Field label="Caption">{version.caption}</Field>
                  <Field label="Call to action">{version.cta}</Field>
                  {version.hashtags.length > 0 ? (
                    <Field label="Hashtags">{version.hashtags.join(" ")}</Field>
                  ) : null}
                  {canEdit && viewingCurrent ? (
                    <Button variant="outline" size="sm" onClick={() => setEditing(true)}>
                      Edit
                    </Button>
                  ) : null}
                  {!viewingCurrent ? (
                    <p className="text-xs text-muted-foreground">
                      This is an older version, kept for history. It cannot be changed.
                    </p>
                  ) : null}
                </>
              )}
            </CardContent>
          </Card>

          {version && version.scene_plan.length > 0 ? (
            <Card>
              <CardHeader>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <CardTitle>Scene plan</CardTitle>
                    <CardDescription>
                      A plan for production. Generate an image per scene, or one full video below.
                    </CardDescription>
                  </div>
                  {canEdit && viewingCurrent ? (
                    <MediaButton
                      label={data.media.video ? "Regenerate video" : "Generate video"}
                      busy={generatingVideo}
                      disabled={generatingScene !== null}
                      onClick={generateVideo}
                    />
                  ) : null}
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                {generatingVideo ? (
                  <p className="text-xs text-muted-foreground">
                    Generating a video can take about a minute. You can keep reviewing scenes meanwhile.
                  </p>
                ) : null}
                {data.media.video ? (
                  <video
                    controls
                    className="w-full max-w-sm rounded-lg border"
                    src={mediaSrc(data.media.video)}
                  >
                    Your browser cannot play this video.
                  </video>
                ) : null}
                <ol className="space-y-3 text-sm">
                  {version.scene_plan.map((scene, index) => {
                    const image = data.media.images.find((item) => item.scene_index === index);
                    return (
                      <li key={index} className="space-y-2 rounded-lg border p-3">
                        <p className="font-medium">
                          Scene {index + 1} · {scene.duration_seconds}s · {scene.purpose}
                        </p>
                        <p className="text-muted-foreground">{scene.visual_description}</p>
                        {scene.on_screen_text ? <p className="mt-1">“{scene.on_screen_text}”</p> : null}
                        {image ? (
                          <img
                            src={mediaSrc(image)}
                            alt={`Scene ${index + 1}: ${scene.purpose}`}
                            className="h-32 w-auto rounded-lg border object-cover"
                          />
                        ) : null}
                        {canEdit && viewingCurrent ? (
                          <MediaButton
                            label={image ? "Regenerate image" : "Generate image"}
                            busy={generatingScene === index}
                            disabled={generatingScene !== null && generatingScene !== index}
                            onClick={() => generateImage(index)}
                          />
                        ) : null}
                      </li>
                    );
                  })}
                </ol>
              </CardContent>
            </Card>
          ) : null}

          {research ? (
            <Card>
              <CardHeader>
                <CardTitle>Research brief</CardTitle>
                <CardDescription>
                  Written by AI without web access. Treat it as a starting point, not verified fact.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                {[
                  { title: "Audience questions", items: research.audience_questions },
                  { title: "Angles", items: research.angles },
                  { title: "Claims to verify", items: research.claims_to_verify },
                  { title: "Limitations", items: research.limitations },
                ].map((group) =>
                  group.items?.length ? (
                    <div key={group.title}>
                      <p className="font-medium">{group.title}</p>
                      <ul className="list-inside list-disc text-muted-foreground">
                        {group.items.map((entry) => (
                          <li key={entry}>{entry}</li>
                        ))}
                      </ul>
                    </div>
                  ) : null,
                )}
              </CardContent>
            </Card>
          ) : null}
        </div>

        <div className="space-y-4">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between gap-2">
                <CardTitle>Brand Guardian</CardTitle>
                {review ? <StatusBadge status={review.status} /> : null}
              </div>
              <CardDescription>An independent AI review of this version.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              {!review ? (
                <p className="text-muted-foreground">Not reviewed.</p>
              ) : review.findings.length === 0 ? (
                <p className="text-muted-foreground">No problems found.</p>
              ) : (
                review.findings.map((finding, index) => (
                  <div key={index} className="space-y-1 rounded-lg border p-3">
                    <div className="flex flex-wrap gap-1">
                      <Badge variant={finding.severity === "blocker" ? "destructive" : "secondary"}>
                        {finding.severity}
                      </Badge>
                      <Badge variant="outline">{finding.check_type.replace("_", " ")}</Badge>
                    </div>
                    <p>“{finding.evidence}”</p>
                    <p className="text-muted-foreground">{finding.recommendation}</p>
                  </div>
                ))
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Human approval</CardTitle>
              <CardDescription>Approval applies only to this exact version.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              {data.status === "approved" ? (
                <Alert>
                  <AlertTitle>Approved</AlertTitle>
                  <AlertDescription>Version {data.current_version} is approved.</AlertDescription>
                </Alert>
              ) : null}
              {data.status === "blocked" ? (
                <Alert variant="destructive">
                  <AlertTitle>Blocked</AlertTitle>
                  <AlertDescription>
                    Fix the Guardian findings and save a new version before approval.
                  </AlertDescription>
                </Alert>
              ) : null}
              {pending && viewingCurrent ? (
                canApprove ? (
                  <>
                    <div className="space-y-2">
                      <Label htmlFor="feedback">Feedback (needed to request changes)</Label>
                      <textarea
                        id="feedback"
                        rows={3}
                        className={textareaClass}
                        value={feedback}
                        onChange={(event) => setFeedback(event.target.value)}
                      />
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <Button
                        disabled={busy}
                        onClick={() =>
                          run(
                            () =>
                              api(`${path}/approvals/${pending.id}/decision`, {
                                method: "POST",
                                body: { approve: true },
                              }),
                            `Version ${data.current_version} approved`,
                            "Could not approve.",
                          )
                        }
                      >
                        Approve this version
                      </Button>
                      <Button
                        variant="outline"
                        disabled={busy || feedback.trim().length < 3}
                        onClick={() =>
                          run(
                            () =>
                              api(`${path}/approvals/${pending.id}/decision`, {
                                method: "POST",
                                body: { approve: false, feedback },
                              }),
                            "Changes requested",
                            "Could not send feedback.",
                          )
                        }
                      >
                        Request changes
                      </Button>
                    </div>
                  </>
                ) : (
                  <p className="text-muted-foreground">Waiting for an owner, admin or manager.</p>
                )
              ) : null}
              {canEdit && viewingCurrent && ["changes_requested", "blocked", "failed"].includes(data.status) ? (
                <div className="space-y-2">
                  <Label htmlFor="revise">Ask AI to revise</Label>
                  <textarea
                    id="revise"
                    rows={3}
                    className={textareaClass}
                    value={feedback}
                    onChange={(event) => setFeedback(event.target.value)}
                  />
                  <Button
                    variant="outline"
                    disabled={busy || feedback.trim().length < 3}
                    onClick={() =>
                      run(
                        () => api(`${path}/revise`, { method: "POST", body: { feedback } }),
                        "New version written and reviewed",
                        "Could not revise.",
                      )
                    }
                  >
                    {busy ? "Revising…" : "Revise with AI"}
                  </Button>
                </div>
              ) : null}
              {data.approvals.length > 0 ? (
                <ul className="space-y-1 border-t pt-3 text-xs text-muted-foreground">
                  {data.approvals.map((approval) => (
                    <li key={approval.id}>
                      Version {approval.content_version}: {approval.decision.replace("_", " ")}
                      {approval.feedback ? ` – ${approval.feedback}` : ""}
                    </li>
                  ))}
                </ul>
              ) : null}
            </CardContent>
          </Card>

          {data.status === "approved" ? (
            <PublishAndResults
              orgBase={base}
              contentId={data.id}
              role={organization.role}
              publication={calendar.data?.items.find((item) => item.content_id === data.id)}
              onChanged={() => {
                calendar.reload();
                reload();
              }}
            />
          ) : null}
        </div>
      </div>
    </>
  );
}
