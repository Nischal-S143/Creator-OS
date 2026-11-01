"use client";

import { useState } from "react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError, api, type CampaignDetail, type Simulation } from "@/lib/api";

const LABELS: Record<string, string> = {
  brand_fit: "Brand fit",
  audience_relevance: "Audience relevance",
  feasibility: "Feasibility",
  differentiation: "Differentiation",
  risk_safety: "Low risk",
  evidence_quality: "Evidence quality",
};

function List({ title, items }: { title: string; items: string[] }) {
  if (items.length === 0) return null;
  return (
    <div>
      <p className="font-medium">{title}</p>
      <ul className="list-inside list-disc text-muted-foreground">
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

export function FlightSimulator({
  path,
  simulation,
  editable,
  onChanged,
}: {
  path: string;
  simulation: Simulation | null;
  editable: boolean;
  onChanged: () => void;
}) {
  const [busy, setBusy] = useState(false);

  async function run() {
    setBusy(true);
    try {
      await api<CampaignDetail>(`${path}/simulate`, { method: "POST" });
      toast.success("Strategies compared");
      onChanged();
    } catch (caught) {
      toast.error(caught instanceof ApiError ? caught.message : "Could not compare strategies.");
    } finally {
      setBusy(false);
    }
  }

  async function select(index: number) {
    setBusy(true);
    try {
      await api<CampaignDetail>(`${path}/simulation/select`, { method: "POST", body: { index } });
      toast.success("Strategy selected. New ideas will follow it.");
      onChanged();
    } catch (caught) {
      toast.error(caught instanceof ApiError ? caught.message : "Could not select this strategy.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <CardTitle>Strategy Comparison</CardTitle>
          {editable ? (
            <Button size="sm" variant="outline" disabled={busy} onClick={run}>
              {busy ? "Comparing…" : simulation ? "Compare again" : "Compare strategies"}
            </Button>
          ) : null}
        </div>
        <CardDescription>
          Compares approaches before you spend on production. Ratings are AI judgement and the total is a
          fixed weighted score. It does not predict reach or results.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4 text-sm">
        {busy && !simulation ? (
          <div className="grid gap-3 md:grid-cols-3" role="status" aria-label="Comparing strategies">
            {[1, 2, 3].map((item) => (
              <Skeleton key={item} className="h-40" />
            ))}
          </div>
        ) : null}
        {!simulation && !busy ? (
          <p className="text-muted-foreground">No comparison yet.</p>
        ) : null}
        {simulation?.strategies.map((strategy, index) => (
          <div
            key={strategy.name}
            className={`space-y-3 rounded-lg border p-4 ${simulation.selected === index ? "ring-2 ring-primary" : ""}`}
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="min-w-0">
                <p className="font-medium">{strategy.name}</p>
                <p className="text-muted-foreground">{strategy.summary}</p>
              </div>
              <div className="flex items-center gap-2">
                {simulation.selected === index ? <Badge>Selected</Badge> : null}
                <Badge variant="secondary">{strategy.total_score} / 100</Badge>
              </div>
            </div>
            <dl className="grid gap-2 sm:grid-cols-2">
              {Object.entries(strategy.ratings).map(([key, rating]) => (
                <div key={key}>
                  <dt className="font-medium">
                    {LABELS[key] ?? key}: {rating.score}/5
                    <span className="ml-1 font-normal text-muted-foreground">
                      (weight {simulation.weights[key]})
                    </span>
                  </dt>
                  <dd className="text-muted-foreground">{rating.reason}</dd>
                </div>
              ))}
            </dl>
            <p>
              <span className="font-medium">Production effort: </span>
              <span className="capitalize text-muted-foreground">{strategy.production_effort}</span>
            </p>
            <List title="Assumptions" items={strategy.assumptions} />
            <List title="Evidence" items={strategy.evidence} />
            <List title="Risks" items={strategy.risks} />
            {editable && simulation.selected !== index ? (
              <Button size="sm" variant="outline" disabled={busy} onClick={() => select(index)}>
                Select this strategy
              </Button>
            ) : null}
          </div>
        ))}
        {simulation ? <List title="Limitations" items={simulation.limitations} /> : null}
      </CardContent>
    </Card>
  );
}
