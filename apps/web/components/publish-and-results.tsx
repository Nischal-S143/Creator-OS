"use client";

import { useState, type FormEvent } from "react";
import { toast } from "sonner";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ApiError, api, can, useResource, type CalendarItem, type ResultReport, type Role } from "@/lib/api";

const METRICS = ["views", "reach", "likes", "comments", "shares", "saves"];
const WINDOWS = ["48h", "7d", "30d"];

function fail(caught: unknown, fallback: string) {
  toast.error(caught instanceof ApiError ? caught.message : fallback);
}

export function PublishAndResults({
  orgBase,
  contentId,
  role,
  publication,
  onChanged,
}: {
  orgBase: string;
  contentId: string;
  role: Role;
  publication: CalendarItem | undefined;
  onChanged: () => void;
}) {
  const path = `${orgBase}/content/${contentId}`;
  const results = useResource<Record<string, ResultReport>>(`${path}/results`);
  const [scheduledFor, setScheduledFor] = useState("");
  const [url, setUrl] = useState("");
  const [window, setWindow] = useState("48h");
  const [values, setValues] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const canPublish = can.approveContent(role);
  const canEnter = can.editCampaign(role);

  async function act(action: () => Promise<unknown>, success: string, fallback: string) {
    setBusy(true);
    try {
      await action();
      toast.success(success);
      onChanged();
      results.reload();
    } catch (caught) {
      fail(caught, fallback);
    } finally {
      setBusy(false);
    }
  }

  function submitSchedule(event: FormEvent) {
    event.preventDefault();
    act(
      () =>
        api(`${path}/schedule`, {
          method: "POST",
          body: { scheduled_for: new Date(scheduledFor).toISOString() },
        }),
      "Scheduled",
      "Could not schedule.",
    );
  }

  function submitPublished(event: FormEvent) {
    event.preventDefault();
    act(
      () => api(`${path}/published`, { method: "POST", body: { url } }),
      "Recorded as published",
      "Could not record this.",
    );
  }

  function submitResults(event: FormEvent) {
    event.preventDefault();
    const numbers = Object.fromEntries(
      Object.entries(values)
        .filter(([, value]) => value !== "")
        .map(([key, value]) => [key, Number(value)]),
    );
    act(
      async () => {
        await api(`${path}/results`, { method: "POST", body: { window, ...numbers } });
        setValues({});
      },
      "Results reviewed",
      "Could not save the results.",
    );
  }

  const reports = results.data ? Object.values(results.data) : [];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Publish and learn</CardTitle>
        <CardDescription>
          Post this approved version yourself, then record it here. Direct posting needs platform accounts.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-5 text-sm">
        {publication?.published_at ? (
          <p>
            <Badge>Published</Badge>{" "}
            <a
              href={publication.url ?? undefined}
              target="_blank"
              rel="noreferrer noopener"
              className="break-all underline underline-offset-4"
            >
              {publication.url}
            </a>
          </p>
        ) : canPublish ? (
          <>
            {publication?.scheduled_for ? (
              <p className="text-muted-foreground">
                Scheduled for {new Date(publication.scheduled_for).toLocaleString()}
              </p>
            ) : null}
            <form onSubmit={submitSchedule} className="flex flex-col gap-2 sm:flex-row sm:items-end">
              <div className="flex-1 space-y-2">
                <Label htmlFor="schedule-at">Schedule for</Label>
                <Input
                  id="schedule-at"
                  type="datetime-local"
                  required
                  value={scheduledFor}
                  onChange={(event) => setScheduledFor(event.target.value)}
                />
              </div>
              <Button type="submit" variant="outline" disabled={busy}>
                Schedule
              </Button>
            </form>
            <form onSubmit={submitPublished} className="flex flex-col gap-2 sm:flex-row sm:items-end">
              <div className="flex-1 space-y-2">
                <Label htmlFor="post-url">Link to the live post</Label>
                <Input
                  id="post-url"
                  type="url"
                  required
                  placeholder="https://"
                  value={url}
                  onChange={(event) => setUrl(event.target.value)}
                />
              </div>
              <Button type="submit" disabled={busy}>
                Mark as published
              </Button>
            </form>
          </>
        ) : (
          <p className="text-muted-foreground">An owner, admin or manager records publishing.</p>
        )}

        {publication?.published_at && canEnter ? (
          <form onSubmit={submitResults} className="space-y-3 border-t pt-4">
            <p className="font-medium">Enter results from the platform</p>
            <div className="space-y-2">
              <Label htmlFor="review-window">Review point</Label>
              <div>
                <select
                  id="review-window"
                  value={window}
                  onChange={(event) => setWindow(event.target.value)}
                  className="h-8 rounded-lg border border-input bg-background px-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  {WINDOWS.map((item) => (
                    <option key={item} value={item}>
                      {item}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              {METRICS.map((metric) => (
                <div key={metric} className="space-y-1">
                  <Label htmlFor={`metric-${metric}`} className="capitalize">
                    {metric}
                  </Label>
                  <Input
                    id={`metric-${metric}`}
                    type="number"
                    min={0}
                    value={values[metric] ?? ""}
                    onChange={(event) => setValues({ ...values, [metric]: event.target.value })}
                  />
                </div>
              ))}
            </div>
            <Button type="submit" disabled={busy}>
              {busy ? "Reviewing…" : "Review results"}
            </Button>
          </form>
        ) : null}

        {reports.map((report) => (
          <div key={report.window} className="space-y-3 border-t pt-4">
            <div className="flex flex-wrap items-center gap-2">
              <p className="font-medium">Review at {report.window}</p>
              <Badge variant="outline">
                {report.comparison.verdict === "compared" ? "Compared" : "Too few posts to compare reliably"}
              </Badge>
            </div>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Measured</TableHead>
                    <TableHead className="text-right">This post</TableHead>
                    <TableHead className="text-right">Brand median</TableHead>
                    <TableHead className="text-right">Ratio</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {Object.entries(report.comparison.metrics).map(([name, metric]) => (
                    <TableRow key={name}>
                      <TableCell className="capitalize">{name}</TableCell>
                      <TableCell className="text-right">{metric.value.toLocaleString()}</TableCell>
                      <TableCell className="text-right">{metric.baseline_median?.toLocaleString() ?? "–"}</TableCell>
                      <TableCell className="text-right">
                        {metric.ratio_to_baseline ? `${metric.ratio_to_baseline}×` : "–"}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
            {report.ai_available ? (
              <>
                <p>{report.summary}</p>
                {report.hypotheses.map((item) => (
                  <div key={item.hypothesis} className="rounded-lg border p-3">
                    <p className="text-xs font-medium text-muted-foreground">Possible reason (AI hypothesis)</p>
                    <p>{item.hypothesis}</p>
                    <p className="mt-1 text-muted-foreground">Test it: {item.suggested_experiment}</p>
                  </div>
                ))}
              </>
            ) : (
              <Alert>
                <AlertDescription>
                  AI was unavailable, so this report has measured numbers only.
                </AlertDescription>
              </Alert>
            )}
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
