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
