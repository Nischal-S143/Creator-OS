/** Sections whose backend is not built yet. They show what is coming and never show invented data. */

export type Wireframe = "table" | "cards" | "calendar" | "chart" | "split" | "timeline";

export type PlannedSection = {
  slug: string;
  title: string;
  description: string;
  phase: string;
  wireframe: Wireframe;
  capabilities: string[];
  needs?: string;
};

export const PLANNED_SECTIONS: PlannedSection[] = [
  {
    slug: "audience",
    title: "Audience Intelligence",
    description: "Turn real audience questions into campaign opportunities.",
    phase: "Phase 4",
    wireframe: "cards",
    capabilities: [
      "Find repeated questions and topic clusters from authorized accounts",
      "See sentiment and content gaps",
      "Approve an opportunity and start a campaign from it",
    ],
    needs: "Connected social accounts with the right permissions",
  },
  {
    slug: "simulator",
    title: "Campaign Flight Simulator",
    description: "Compare campaign strategies before spending on production.",
    phase: "Phase 5",
    wireframe: "cards",
    capabilities: [
      "Generate alternative strategies from a brief",
      "Compare brand fit, audience relevance, cost and risk",
      "See the evidence and assumptions behind every score",
    ],
  },
  {
    slug: "video",
    title: "Video Editor",
    description: "Assemble and preview generated video.",
    phase: "Phase 6",
    wireframe: "timeline",
    capabilities: [
      "Review scenes, voiceover and subtitles on a timeline",
      "Preview platform-specific exports",
      "Track provenance and licensing for each asset",
    ],
    needs: "Image, video and voice generation providers",
  },
  {
    slug: "calendar",
    title: "Publishing Calendar",
    description: "Plan and track approved posts across clients.",
    phase: "Phase 9",
    wireframe: "calendar",
    capabilities: [
      "Schedule approved content",
      "See status across clients and platforms",
      "Reconcile uncertain results before any retry",
    ],
    needs: "Connected social accounts",
  },
  {
    slug: "social-accounts",
    title: "Social Accounts",
    description: "Connect client accounts through official platform sign-in.",
    phase: "Phase 9",
    wireframe: "table",
    capabilities: [
      "Connect accounts per client",
      "See permissions and token expiry",
      "Disconnect at any time",
    ],
    needs: "Approved developer apps on each platform",
  },
  {
    slug: "analytics",
    title: "Analytics",
    description: "Measured results for published content.",
    phase: "Phase 10",
    wireframe: "chart",
    capabilities: [
      "Track reach, engagement and watch time from platform data",
      "Review each post at 48 hours, 7 days and 30 days",
      "Approve lessons that shape future campaigns",
    ],
    needs: "Published posts and platform metrics access",
  },
  {
    slug: "creative-autopsy",
    title: "Creative Autopsy",
    description: "Understand how creative choices relate to results.",
    phase: "Phase 10",
    wireframe: "timeline",
    capabilities: [
      "Break down hooks, scenes, pacing and calls to action",
      "See measured facts apart from AI hypotheses",
      "Turn findings into measurable experiments",
    ],
  },
  {
    slug: "intelligence",
    title: "Agency Intelligence",
    description: "Privacy-safe patterns across your client brands.",
    phase: "Phase 11",
    wireframe: "chart",
    capabilities: [
      "See aggregate patterns, never raw client data",
      "Control which brands contribute",
      "Review a log of contributions and access",
    ],
  },
  {
    slug: "usage",
    title: "Usage and Billing",
    description: "Understand AI usage and costs for your agency.",
    phase: "Phase 12",
    wireframe: "chart",
    capabilities: [
      "Track AI usage and generation costs",
      "See limits for your plan",
      "Manage billing",
    ],
    needs: "A billing provider and pricing",
  },
];

export function findSection(slug: string) {
  return PLANNED_SECTIONS.find((section) => section.slug === slug);
}
