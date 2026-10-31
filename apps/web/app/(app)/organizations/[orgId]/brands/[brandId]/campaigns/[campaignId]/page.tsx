"use client";

import { useRouter } from "next/navigation";
import { use, useState } from "react";
import { toast } from "sonner";

import { useOrg } from "@/components/org-shell";
import { PageHeader } from "@/components/page-header";
import { EmptyState, ErrorState, LoadingRows } from "@/components/states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError, api, can, useResource, type CampaignDetail, type ContentDetail } from "@/lib/api";

export default function CampaignPage({
  params,
}: {
  params: Promise<{ brandId: string; campaignId: string }>;
}) {
  const { brandId, campaignId } = use(params);
  const organization = useOrg();
  const brandHref = `/organizations/${organization.id}/brands/${brandId}`;
  const path = `${brandHref}/campaigns/${campaignId}`;
  const { data, error, loading, reload } = useResource<CampaignDetail>(path);
  const [generating, setGenerating] = useState(false);
  const [selecting, setSelecting] = useState<string | null>(null);
  const editable = can.editCampaign(organization.role);
  const router = useRouter();
  const [creating, setCreating] = useState<string | null>(null);

  async function createContent(scenarioId: string, kind: "organic" | "ad") {
    setCreating(`${scenarioId}:${kind}`);
    try {
      const content = await api<ContentDetail>(`${brandHref}/content`, {
        method: "POST",
        body: { scenario_id: scenarioId, kind },
      });
      router.push(`/organizations/${organization.id}/content-studio/${content.id}`);
    } catch (caught) {
      toast.error(caught instanceof ApiError ? caught.message : "Could not create the content.");
      setCreating(null);
    }
  }

  async function generate() {
    setGenerating(true);
    try {
      await api<CampaignDetail>(`${path}/generate`, { method: "POST" });
      toast.success("Three new ideas are ready");
      reload();
    } catch (caught) {
      toast.error(caught instanceof ApiError ? caught.message : "Could not generate ideas.");
    } finally {
      setGenerating(false);
    }
  }

  async function select(id: string) {
    setSelecting(id);
    try {
      await api<CampaignDetail>(`${path}/scenarios/${id}/select`, { method: "POST" });
      toast.success("Idea selected");
      reload();
    } catch (caught) {
      toast.error(caught instanceof ApiError ? caught.message : "Could not select this idea.");
    } finally {
      setSelecting(null);
    }
  }

  if (loading) return <LoadingRows />;
  if (error) return <ErrorState message={error.message} onRetry={reload} />;
  if (!data) return null;

  return (
    <div className="space-y-6">
      <PageHeader
        title={data.name}
        description={data.objective}
        back={{ href: `${brandHref}?tab=campaigns`, label: "Back to client" }}
        actions={
          editable ? (
            <Button onClick={generate} disabled={generating}>
              {generating
                ? "Generating ideas…"
                : data.scenarios.length > 0
                  ? "Generate new ideas"
                  : "Generate three ideas"}
            </Button>
          ) : null
        }
      />

      {generating ? (
        <div className="grid gap-4 md:grid-cols-3" role="status" aria-label="Generating ideas">
          {[1, 2, 3].map((item) => (
            <Skeleton key={item} className="h-48" />
          ))}
        </div>
      ) : data.scenarios.length === 0 ? (
        <EmptyState title="No ideas yet">
          Ideas need an approved brand profile for this client.
        </EmptyState>
      ) : (
        <div className="grid gap-4 md:grid-cols-3">
          {data.scenarios.map((scenario) => (
            <Card key={scenario.id} className={scenario.selected ? "ring-2 ring-primary" : undefined}>
              <CardHeader>
                <CardTitle className="text-base">{scenario.title}</CardTitle>
                <div className="flex flex-wrap gap-1">
                  <Badge variant="secondary">{scenario.platform}</Badge>
                  <Badge variant="outline">{scenario.content_format}</Badge>
                  {scenario.selected ? <Badge>Selected</Badge> : null}
                </div>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                <p className="font-medium">{scenario.hook}</p>
                <p className="text-muted-foreground">{scenario.description}</p>
                {editable && !scenario.selected ? (
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={selecting !== null}
                    onClick={() => select(scenario.id)}
                  >
                    Select this idea
                  </Button>
                ) : null}
                {editable && scenario.selected ? (
                  <div className="flex flex-wrap gap-2">
                    <Button
                      size="sm"
                      disabled={creating !== null}
                      onClick={() => createContent(scenario.id, "organic")}
                    >
                      {creating === `${scenario.id}:organic` ? "Agents working…" : "Create content"}
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={creating !== null}
                      onClick={() => createContent(scenario.id, "ad")}
                    >
                      {creating === `${scenario.id}:ad` ? "Agents working…" : "Create ad"}
                    </Button>
                  </div>
                ) : null}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {data.runs.length > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Run history</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2 text-sm">
              {data.runs.map((run) => (
                <li key={run.id} className="flex flex-wrap items-center gap-2">
                  <Badge variant={run.status === "failed" ? "destructive" : "secondary"}>
                    {run.status}
                  </Badge>
                  <span className="text-muted-foreground">
                    {new Date(run.started_at).toLocaleString()}
                    {run.model ? ` · ${run.model}` : ""}
                    {run.detail.memory_used === true ? " · used agent memory" : ""}
                  </span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
