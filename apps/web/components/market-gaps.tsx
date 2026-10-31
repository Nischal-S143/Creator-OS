"use client";

import { useState } from "react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiError, api, type MarketGapReport } from "@/lib/api";

export function MarketGaps({ base }: { base: string }) {
  const [report, setReport] = useState<MarketGapReport | null>(null);
  const [busy, setBusy] = useState(false);

  async function run() {
    setBusy(true);
    try {
      setReport(await api<MarketGapReport>(`${base}/market-gaps`, { method: "POST" }));
    } catch (caught) {
      toast.error(caught instanceof ApiError ? caught.message : "Could not look for gaps.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Market gaps</CardTitle>
        <CardDescription>
          Topics this brand may be missing. AI has no market data here, so each one is a hypothesis to
          test, not a finding.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4 text-sm">
        <Button variant="outline" size="sm" onClick={run} disabled={busy}>
          {busy ? "Thinking…" : report ? "Look again" : "Find possible gaps"}
        </Button>
        {report?.gaps.map((gap) => (
          <div key={gap.topic} className="space-y-1 rounded-lg border p-3">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-medium">{gap.topic}</span>
              <Badge variant="outline">{gap.confidence} confidence</Badge>
            </div>
            <p className="text-muted-foreground">{gap.why_it_may_be_open}</p>
            <p className="text-xs font-medium">Evidence to collect</p>
            <ul className="list-inside list-disc text-xs text-muted-foreground">
              {gap.evidence_to_collect.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
