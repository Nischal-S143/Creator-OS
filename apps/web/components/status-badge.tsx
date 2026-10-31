import { Badge } from "@/components/ui/badge";

const LABELS: Record<string, { label: string; variant: "default" | "secondary" | "outline" | "destructive" }> = {
  generating: { label: "Generating", variant: "secondary" },
  failed: { label: "Failed", variant: "destructive" },
  blocked: { label: "Blocked by Guardian", variant: "destructive" },
  in_review: { label: "Waiting for approval", variant: "secondary" },
  changes_requested: { label: "Changes requested", variant: "outline" },
  approved: { label: "Approved", variant: "default" },
  pending: { label: "Pending", variant: "secondary" },
  superseded: { label: "Replaced", variant: "outline" },
  PASS: { label: "Pass", variant: "default" },
  NEEDS_REVIEW: { label: "Needs review", variant: "secondary" },
  BLOCKED: { label: "Blocked", variant: "destructive" },
};

export function StatusBadge({ status }: { status: string }) {
  const entry = LABELS[status] ?? { label: status, variant: "outline" as const };
  return <Badge variant={entry.variant}>{entry.label}</Badge>;
}
