"use client";

import { CheckCircle2Icon, CircleIcon } from "lucide-react";
import Link from "next/link";
import { use } from "react";

import { useOrg } from "@/components/org-shell";
import { PageHeader } from "@/components/page-header";
import { ErrorState, LoadingRows } from "@/components/states";
import { StatusBadge } from "@/components/status-badge";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useResource, type CampaignReport } from "@/lib/api";

function Step({
  done,
  title,
  children,
}: {
  done: boolean;
  title: string;
  children?: React.ReactNode;
}) {
  return (
    <li className="flex gap-3">
      {done ? (
        <CheckCircle2Icon className="mt-0.5 size-4 shrink-0 text-primary" aria-label="Done" />
      ) : (
        <CircleIcon className="mt-0.5 size-4 shrink-0 text-muted-foreground" aria-label="Not done" />
      )}
      <div className="min-w-0 flex-1">
        <p className="font-medium">{title}</p>
        {children ? <div className="mt-1 text-muted-foreground">{children}</div> : null}
      </div>
    </li>
  );
}

export default function CampaignReportPage({
  params,
}: {
  params: Promise<{ brandId: string; campaignId: string }>;
}) {
  const { brandId, campaignId } = use(params);
  const organization = useOrg();
  const base = `/organizations/${organization.id}`;
  const brandBase = `${base}/brands/${brandId}`;
  const { data, error, loading, reload } = useResource<CampaignReport>(
    `${brandBase}/campaigns/${campaignId}/report`,
  );

  if (loading) return <LoadingRows />;
  if (error) return <ErrorState message={error.message} onRetry={reload} />;
  if (!data) return null;

  return (
    <div className="space-y-6">
      <PageHeader
        title={`Report: ${data.name}`}
        description={data.objective}
        back={{ href: `${brandBase}/campaigns/${campaignId}`, label: "Back to campaign" }}
      />

      <Card>
        <CardHeader>
          <CardTitle>From plan to learning</CardTitle>
          <CardDescription>Everything recorded for this campaign, in order.</CardDescription>
        </CardHeader>
        <CardContent>
          <ol className="space-y-4 text-sm">
            <Step done={Boolean(data.strategy)} title="Strategy chosen">
              {data.strategy
                ? `${data.strategy.name} (${data.strategy.total_score} / 100)`
                : "No strategy selected in the Flight Simulator."}
            </Step>
            <Step done={data.lessons_used.length > 0} title="Past lessons applied">
              {data.lessons_used.length > 0 ? (
                <ul className="list-inside list-disc">
                  {data.lessons_used.map((lesson) => (
                    <li key={lesson.lesson}>
                      {lesson.lesson} <span className="text-xs">(from {lesson.source})</span>
                    </li>
                  ))}
                </ul>
              ) : (
                "The latest ideas did not use any approved lessons."
              )}
            </Step>
            <Step done={Boolean(data.selected_idea)} title="Idea selected">
              {data.selected_idea ?? "No idea selected yet."}
            </Step>
            <Step done={data.content.length > 0} title="Content produced">
              {data.content.length} {data.content.length === 1 ? "item" : "items"}
            </Step>
            <Step
              done={data.content.some((item) => item.status === "approved")}
              title="Approved by a person"
            />
            <Step
              done={data.content.some((item) => item.published_at)}
              title="Published and recorded"
            />
            <Step done={data.lessons_learned.length > 0} title="Lessons proposed from results">
              {data.lessons_learned.length > 0
                ? `${data.lessons_learned.filter((lesson) => lesson.status === "approved").length} approved of ${data.lessons_learned.length}`
                : null}
            </Step>
          </ol>
        </CardContent>
      </Card>

      {data.content.length > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle>Content</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            {data.content.map((item) => (
              <div key={item.id} className="space-y-2 rounded-lg border p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <Link
                    href={`${base}/content-studio/${item.id}`}
                    className="font-medium underline-offset-4 hover:underline"
                  >
                    {item.title}
                  </Link>
                  <div className="flex flex-wrap gap-1">
                    <Badge variant="outline">Version {item.version}</Badge>
                    {item.kind === "ad" ? <Badge variant="outline">Ad</Badge> : null}
                    {item.guardian_status ? <StatusBadge status={item.guardian_status} /> : null}
                    <StatusBadge status={item.status} />
                  </div>
                </div>
                {item.url ? (
                  <a
                    href={item.url}
                    target="_blank"
                    rel="noreferrer noopener"
                    className="block break-all text-xs underline underline-offset-4"
                  >
                    {item.url}
                  </a>
                ) : null}
                {item.reviews.map((review) => (
                  <p key={review.window} className="text-muted-foreground">
                    {review.window}:{" "}
                    {Object.entries(review.metrics)
                      .map(
                        ([name, metric]) =>
                          `${name} ${metric.value.toLocaleString()}${metric.ratio_to_baseline ? ` (${metric.ratio_to_baseline}× median)` : ""}`,
                      )
                      .join(" · ")}
                  </p>
                ))}
              </div>
            ))}
          </CardContent>
        </Card>
      ) : null}

      {data.lessons_learned.length > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle>What this campaign taught</CardTitle>
            <CardDescription>AI hypotheses. Only approved ones reach future campaigns.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            {data.lessons_learned.map((lesson) => (
              <div key={lesson.id} className="flex flex-wrap items-start justify-between gap-2 rounded-lg border p-3">
                <p className="min-w-0 flex-1">{lesson.text}</p>
                <Badge
                  variant={lesson.status === "approved" ? "default" : "secondary"}
                  className="capitalize"
                >
                  {lesson.status}
                </Badge>
              </div>
            ))}
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
