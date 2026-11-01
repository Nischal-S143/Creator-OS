"use client";

import { useOrg } from "@/components/org-shell";
import { PageHeader } from "@/components/page-header";
import { EmptyState, ErrorState, LoadingRows } from "@/components/states";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { can, useResource, type AgentRunRow } from "@/lib/api";

type Status = "working" | "billing" | "accounts" | "planned";

const STATUS: Record<Status, { label: string; variant: "default" | "secondary" | "outline" }> = {
  working: { label: "Working", variant: "default" },
  billing: { label: "Needs Google billing", variant: "secondary" },
  accounts: { label: "Needs platform accounts", variant: "secondary" },
  planned: { label: "Not built yet", variant: "outline" },
};

const AGENTS: { name: string; job: string; status: Status }[] = [
  { name: "Understanding", job: "Reads an uploaded document and drafts the brand profile", status: "working" },
  { name: "Strategy", job: "Generates campaign ideas from approved brand context", status: "working" },
  { name: "Audience Intelligence", job: "Groups pasted comments into topics and opportunities", status: "working" },
  { name: "Strategy Comparison", job: "Compares three campaign strategies with a transparent score", status: "working" },
  { name: "Research", job: "Prepares an unverified brief, with claims to check", status: "working" },
  { name: "Script", job: "Writes hooks, scripts, captions and calls to action", status: "working" },
  { name: "Visual", job: "Plans scenes for each script", status: "working" },
  { name: "Brand Guardian", job: "Independently reviews text against brand rules", status: "working" },
  { name: "Ad Creation", job: "Writes ad copy, reviewed like any other content", status: "working" },
  { name: "Market Gap", job: "Suggests topics to test, as hypotheses", status: "working" },
  { name: "Image", job: "Creates an image for a scene, in Content Studio", status: "working" },
  { name: "Video", job: "Creates a short video for the content, in Content Studio", status: "working" },
  { name: "Voice", job: "Creates voiceover and subtitles", status: "planned" },
  { name: "Publishing", job: "Posts approved content to social platforms", status: "accounts" },
  { name: "Analytics and Feedback", job: "Compares results in code, then proposes lessons for approval", status: "working" },
];

const RUN_NAMES: Record<string, string> = {
  brand_profile_extraction: "Understanding",
  campaign_ideas: "Strategy",
  content_production: "Research, Script, Visual, Guardian",
  market_gap: "Market Gap",
  flight_simulator: "Strategy Comparison",
  audience_intelligence: "Audience Intelligence",
  image_generation: "Image",
  video_generation: "Video",
};

export default function AgentsPage() {
  const organization = useOrg();
  const { data, error, loading, reload } = useResource<{ items: AgentRunRow[] }>(
    `/organizations/${organization.id}/agent-runs`,
  );

  return (
    <>
      <PageHeader
        title="AI Team"
        description="Each agent has one job. They run in a fixed order, and people approve the results. Each step is logged to Meko."
      />
      <div className="space-y-6">
        <div className="grid gap-3 sm:grid-cols-2">
          {AGENTS.map((agent) => (
            <Card key={agent.name} size="sm">
              <CardContent className="space-y-1">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="font-medium">{agent.name}</p>
                  <Badge variant={STATUS[agent.status].variant}>{STATUS[agent.status].label}</Badge>
                </div>
                <p className="text-sm text-muted-foreground">{agent.job}</p>
              </CardContent>
            </Card>
          ))}
        </div>
        <Card>
          <CardHeader>
            <CardTitle>Recent runs</CardTitle>
            <CardDescription>What the agents have actually done for this agency.</CardDescription>
          </CardHeader>
          <CardContent>
            {!can.viewCampaigns(organization.role) ? (
              <p className="text-sm text-muted-foreground">Your role cannot view agent runs.</p>
            ) : loading ? (
              <LoadingRows rows={2} />
            ) : error ? (
              <ErrorState message={error.message} onRetry={reload} />
            ) : data?.items.length === 0 ? (
              <EmptyState title="No runs yet">
                Upload a document on a client&apos;s Brand Brain tab to start.
              </EmptyState>
            ) : (
              <ul className="divide-y text-sm">
                {data?.items.map((run) => (
                  <li key={run.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
                    <span className="min-w-0">
                      <span className="block truncate font-medium">
                        {RUN_NAMES[run.graph_name] ?? run.graph_name}
                      </span>
                      <span className="block truncate text-muted-foreground">
                        {run.brand_name} · {new Date(run.started_at).toLocaleString()}
                      </span>
                    </span>
                    <Badge variant={run.status === "failed" ? "destructive" : "secondary"}>{run.status}</Badge>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>
    </>
  );
}
