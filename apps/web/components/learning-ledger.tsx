"use client";

import { useState } from "react";
import { toast } from "sonner";

import { EmptyState, ErrorState, LoadingRows } from "@/components/states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiError, api, can, useResource, type Lesson, type Role } from "@/lib/api";

export function LearningLedger({ base, role }: { base: string; role: Role }) {
  const { data, error, loading, reload } = useResource<{ items: Lesson[] }>(`${base}/lessons`);
  const [busy, setBusy] = useState(false);
  const canDecide = can.approveProfile(role);

  async function decide(lesson: Lesson, approve: boolean) {
    setBusy(true);
    try {
      await api(`${base}/lessons/${lesson.id}/decision`, { method: "POST", body: { approve } });
      toast.success(approve ? "Lesson approved. Future campaigns will use it." : "Lesson rejected");
      reload();
    } catch (caught) {
      toast.error(caught instanceof ApiError ? caught.message : "Could not save this decision.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Learning Ledger</CardTitle>
        <CardDescription>
          Lessons from real results. Nothing reaches future campaigns until a person approves it, and each
          lesson shows its evidence and a review date.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        {loading ? <LoadingRows rows={1} /> : null}
        {error ? <ErrorState message={error.message} onRetry={reload} /> : null}
        {data?.items.length === 0 ? (
          <EmptyState title="No lessons yet">
            Lessons appear after you enter results for a published post.
          </EmptyState>
        ) : null}
        {data?.items.map((lesson) => (
          <div key={lesson.id} className="space-y-2 rounded-lg border p-4">
            <div className="flex flex-wrap items-center gap-1">
              <Badge variant={lesson.status === "approved" ? "default" : "secondary"} className="capitalize">
                {lesson.status}
              </Badge>
              <Badge variant="outline">{lesson.confidence} confidence</Badge>
              <Badge variant="outline">Compared with {lesson.sample_size} posts</Badge>
            </div>
            <p className="font-medium">{lesson.text}</p>
            <p className="text-muted-foreground">Seen: {lesson.observation}</p>
            <p className="text-muted-foreground">Test it: {lesson.suggested_experiment}</p>
            <p className="text-xs text-muted-foreground">
              Source: {lesson.source_title}, {lesson.window} review
              {lesson.review_at ? ` · review by ${new Date(lesson.review_at).toLocaleDateString()}` : ""}
            </p>
            {canDecide && lesson.status === "proposed" ? (
              <div className="flex gap-2">
                <Button size="sm" disabled={busy} onClick={() => decide(lesson, true)}>
                  Approve lesson
                </Button>
                <Button size="sm" variant="outline" disabled={busy} onClick={() => decide(lesson, false)}>
                  Reject
                </Button>
              </div>
            ) : null}
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
