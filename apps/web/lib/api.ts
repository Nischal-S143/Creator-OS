"use client";

import { useCallback, useEffect, useState } from "react";

export type Role =
  | "owner"
  | "admin"
  | "manager"
  | "editor"
  | "analyst"
  | "client_approver";

export const ROLE_LABELS: Record<Role, string> = {
  owner: "Owner",
  admin: "Admin",
  manager: "Manager",
  editor: "Editor",
  analyst: "Analyst",
  client_approver: "Client approver",
};

export type Organization = {
  id: string;
  name: string;
  slug: string;
  plan: string;
  status: string;
  created_at: string;
  role: Role;
};
export type Me = { id: string; email: string; organizations: Organization[] };
export type Brand = {
  id: string;
  organization_id: string;
  name: string;
  slug: string;
  industry: string | null;
  website_url: string | null;
  owner_id: string;
  created_at: string;
};
export type Member = {
  id: string;
  user_id: string;
  email: string;
  role: Role;
  status: "active" | "removed";
};
export type BrandDocument = {
  id: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  created_at: string;
};
export type BrandProfile = {
  id: string;
  version: number;
  status: "proposed" | "approved" | "rejected" | "superseded";
  voice: string;
  tone: string;
  audience: string;
  content_pillars: string[];
  restrictions: string[];
  memory_status: "not_synced" | "synced" | "failed";
};
export type Campaign = {
  id: string;
  brand_id: string;
  name: string;
  objective: string;
  audience: string | null;
  created_at: string;
};
export type Scenario = {
  id: string;
  title: string;
  hook: string;
  description: string;
  platform: string;
  content_format: string;
  selected: boolean;
};
export type AgentRun = {
  id: string;
  graph_name: string;
  status: "running" | "succeeded" | "failed";
  model: string | null;
  error: string | null;
  detail: Record<string, unknown>;
  started_at: string;
};
export type CampaignDetail = Campaign & { scenarios: Scenario[]; runs: AgentRun[] };
export type ContentStatus =
  | "generating"
  | "failed"
  | "blocked"
  | "in_review"
  | "changes_requested"
  | "approved";
export type ContentRow = {
  id: string;
  brand_id: string;
  campaign_id: string;
  title: string;
  platform: string;
  kind: "organic" | "ad";
  status: ContentStatus;
  current_version: number;
  created_at: string;
  brand_name?: string;
};
export type ContentVersion = {
  version: number;
  source: "agent" | "human";
  hook: string;
  script: string;
  caption: string;
  cta: string;
  hashtags: string[];
  scene_plan: {
    purpose: string;
    visual_description: string;
    on_screen_text: string;
    duration_seconds: number;
  }[];
  research: {
    audience_questions?: string[];
    angles?: string[];
    claims_to_verify?: string[];
    limitations?: string[];
  };
  content_hash: string;
};
export type ContentDetail = ContentRow & {
  version: ContentVersion | null;
  versions: number[];
  reviews: {
    id: string;
    content_version: number;
    status: string;
    findings: { check_type: string; severity: string; evidence: string; recommendation: string }[];
  }[];
  approvals: {
    id: string;
    content_version: number;
    decision: string;
    feedback: string | null;
  }[];
};
export type PendingApproval = {
  approval_id: string;
  content: ContentRow;
  brand_name: string;
  content_version: number;
  guardian_status: string | null;
};
export type GuardianRow = {
  id: string;
  content_id: string;
  title: string;
  brand_name: string;
  content_version: number;
  status: string;
  findings: number;
};
export type MarketGapReport = {
  gaps: {
    topic: string;
    why_it_may_be_open: string;
    evidence_to_collect: string[];
    confidence: string;
  }[];
  limitations: string[];
};
export type Page<T> = { items: T[]; total: number; limit: number; offset: number };

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

function errorMessage(body: { detail?: unknown }, status: number): string {
  if (typeof body.detail === "string") return body.detail;
  if (Array.isArray(body.detail)) {
    return body.detail
      .map((item: { loc?: string[]; msg?: string }) => {
        const field = item.loc?.at(-1);
        return field ? `${field}: ${item.msg}` : item.msg;
      })
      .join("; ");
  }
  return `Something went wrong (${status}).`;
}

export async function request<T>(
  url: string,
  options: { method?: string; body?: unknown } = {},
): Promise<T> {
  const response = await fetch(url, {
    method: options.method ?? "GET",
    headers: { "Content-Type": "application/json" },
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    // An expired session on an app page goes back to sign-in. Sign-in failures stay on the form.
    if (response.status === 401 && url.startsWith("/api/backend/")) {
      await fetch("/api/session/logout", { method: "POST" });
      window.location.assign("/sign-in");
    }
    throw new ApiError(errorMessage(body, response.status), response.status);
  }
  return body as T;
}

export async function uploadFile<T>(path: string, file: File): Promise<T> {
  const form = new FormData();
  form.append("file", file);
  const response = await fetch(`/api/backend${path}`, { method: "POST", body: form });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new ApiError(errorMessage(body, response.status), response.status);
  return body as T;
}

export function api<T>(path: string, options?: { method?: string; body?: unknown }) {
  return request<T>(`/api/backend${path}`, options);
}

/** Loads a resource, with loading and error states and a reload function. */
export function useResource<T>(path: string) {
  const [state, setState] = useState<{
    path: string;
    version: number;
    data?: T;
    error?: ApiError;
  } | null>(null);
  const [version, setVersion] = useState(0);

  useEffect(() => {
    let cancelled = false;
    api<T>(path)
      .then((data) => {
        if (!cancelled) setState({ path, version, data });
      })
      .catch((error: ApiError) => {
        if (!cancelled) setState({ path, version, error });
      });
    return () => {
      cancelled = true;
    };
  }, [path, version]);

  const reload = useCallback(() => setVersion((value) => value + 1), []);
  const current = state?.path === path ? state : null;
  return {
    data: current?.data,
    error: current?.error,
    loading: current === null,
    reload,
  };
}

export function slugify(name: string): string {
  return name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 100);
}

/** Mirrors the backend role rules for showing controls. The backend still enforces them. */
export const can = {
  manageMembers: (role: Role) => role === "owner" || role === "admin",
  viewMembers: (role: Role) => ["owner", "admin", "manager"].includes(role),
  viewBrands: (role: Role) => role !== "client_approver",
  createBrand: (role: Role) => role === "owner" || role === "admin",
  editBrand: (role: Role) => ["owner", "admin", "manager", "editor"].includes(role),
  approveProfile: (role: Role) => ["owner", "admin", "manager"].includes(role),
  viewCampaigns: (role: Role) => role !== "client_approver",
  approveContent: (role: Role) => ["owner", "admin", "manager"].includes(role),
  editCampaign: (role: Role) => ["owner", "admin", "manager", "editor"].includes(role),
};
