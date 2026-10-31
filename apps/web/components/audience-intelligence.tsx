"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { EmptyState, ErrorState, LoadingRows } from "@/components/states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { ApiError, api, can, useResource, type AudienceReport, type Campaign, type Role } from "@/lib/api";

export function AudienceIntelligence({ base, role }: { base: string; role: Role }) {
  const { data, error, loading, reload } = useResource<{ report: AudienceReport | null }>(`${base}/audience`);
  const [comments, setComments] = useState("");
  const [busy, setBusy] = useState(false);
  const router = useRouter();
  const editable = can.editCampaign(role);
  const report = data?.report;

  async function analyze() {
    setBusy(true);
    try {
      await api(`${base}/audience/analyze`, { method: "POST", body: { comments } });
      toast.success("Comments analyzed");
      setComments("");
      reload();
    } catch (caught) {
      toast.error(caught instanceof ApiError ? caught.message : "Could not analyze these comments.");
    } finally {
      setBusy(false);
    }
  }

  async function startCampaign(index: number) {
    setBusy(true);
    try {
      const campaign = await api<Campaign>(`${base}/audience/campaign`, {
        method: "POST",
        body: { topic_index: index },
      });
      toast.success("Campaign created");
      router.push(`${base}/campaigns/${campaign.id}`);
    } catch (caught) {
      toast.error(caught instanceof ApiError ? caught.message : "Could not create the campaign.");
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      {editable ? (
        <Card>
          <CardHeader>
            <CardTitle>Analyze audience comments</CardTitle>
            <CardDescription>
              Paste comments or questions you have permission to use, one per line. Connecting social
              accounts directly comes later. Raw comments are analyzed but not stored.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="space-y-2">
              <Label htmlFor="audience-comments">Comments</Label>
              <textarea
                id="audience-comments"
                rows={7}
                maxLength={100000}
                value={comments}
                onChange={(event) => setComments(event.target.value)}
                className="w-full rounded-lg border border-input bg-transparent px-2.5 py-1.5 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
              />
            </div>
            <Button disabled={busy || comments.trim().length < 3} onClick={analyze}>
              {busy ? "Analyzing…" : "Analyze comments"}
            </Button>
          </CardContent>
        </Card>
      ) : null}

      {loading ? <LoadingRows rows={2} /> : null}
      {error ? <ErrorState message={error.message} onRetry={reload} /> : null}
      {data && !report ? (
        <EmptyState title="No analysis yet">Topics and opportunities appear here after an analysis.</EmptyState>
      ) : null}
      {report ? (
        <Card>
          <CardHeader>
            <CardTitle>Topics and opportunities</CardTitle>
            <CardDescription>
              From {report.comments_analyzed} comments, after removing {report.comments_removed} duplicates or
              spam. Counts and scores are calculated by software; topics and angles are AI suggestions.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            {report.topics.map((topic, index) => (
              <div key={topic.topic} className="space-y-2 rounded-lg border p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="font-medium">{topic.topic}</p>
                  <div className="flex flex-wrap gap-1">
                    <Badge variant="secondary">Opportunity {topic.opportunity_score} / 100</Badge>
                    <Badge variant="outline">{topic.comment_count} comments</Badge>
                    <Badge variant="outline">{topic.sentiment}</Badge>
                    {topic.content_gap ? <Badge variant="outline">Content gap</Badge> : null}
                  </div>
                </div>
                <ul className="list-inside list-disc text-muted-foreground">
                  {topic.representative_questions.map((question) => (
                    <li key={question}>{question}</li>
                  ))}
                </ul>
                <p>
                  <span className="font-medium">Suggested angle: </span>
                  {topic.suggested_angle}
                </p>
                {editable ? (
                  <Button size="sm" variant="outline" disabled={busy} onClick={() => startCampaign(index)}>
                    Start a campaign from this
                  </Button>
                ) : null}
              </div>
            ))}
            {report.limitations.length > 0 ? (
              <p className="text-xs text-muted-foreground">Limits: {report.limitations.join(" ")}</p>
            ) : null}
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
