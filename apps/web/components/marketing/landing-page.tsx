import {
  BarChart3Icon,
  BotIcon,
  BrainIcon,
  FileTextIcon,
  GaugeIcon,
  ImageIcon,
  LightbulbIcon,
  type LucideIcon,
  MegaphoneIcon,
  ShieldCheckIcon,
} from "lucide-react";
import Link from "next/link";

import { Logo, LogoMark } from "@/components/logo";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

const ORBIT_AGENTS: { label: string; Icon: LucideIcon; color: string }[] = [
  { label: "Strategy", Icon: MegaphoneIcon, color: "oklch(0.62 0.19 300)" },
  { label: "Guardian", Icon: ShieldCheckIcon, color: "oklch(0.68 0.17 165)" },
  { label: "Research", Icon: FileTextIcon, color: "oklch(0.7 0.15 230)" },
  { label: "Visual", Icon: ImageIcon, color: "oklch(0.68 0.19 350)" },
  { label: "Audience", Icon: LightbulbIcon, color: "oklch(0.75 0.16 75)" },
  { label: "Analytics", Icon: BarChart3Icon, color: "oklch(0.6 0.18 268)" },
];

const TRUST: { title: string; text: string; Icon: LucideIcon }[] = [
  {
    title: "Human approval, always",
    text: "Changed content needs new approval. No agent publishes on its own, ever.",
    Icon: ShieldCheckIcon,
  },
  {
    title: "Durable brand memory",
    text: "An approved fact becomes part of a client's brand brain. Uncertain claims never stick without review.",
    Icon: BrainIcon,
  },
  {
    title: "Numbers you can trust",
    text: "Scores and performance comparisons are computed from real data in code, never guessed by a model.",
    Icon: GaugeIcon,
  },
];

const AGENTS: { name: string; job: string; Icon: LucideIcon }[] = [
  { name: "Understanding", job: "Reads an uploaded document and drafts the brand profile", Icon: BotIcon },
  { name: "Strategy", job: "Generates campaign ideas from approved brand context", Icon: MegaphoneIcon },
  { name: "Audience Intelligence", job: "Groups real comments into topics and opportunities", Icon: LightbulbIcon },
  { name: "Strategy Comparison", job: "Scores competing strategies with a transparent breakdown", Icon: GaugeIcon },
  { name: "Research, Script, Visual", job: "Drafts hooks, scripts, captions and scene plans", Icon: FileTextIcon },
  { name: "Brand Guardian", job: "Independently reviews every piece against brand rules", Icon: ShieldCheckIcon },
  { name: "Image and Video", job: "Generates on-brand visuals for approved scripts", Icon: ImageIcon },
  { name: "Analytics and Feedback", job: "Compares real results to baselines and proposes lessons", Icon: BarChart3Icon },
];

const HOW: { title: string; text: string }[] = [
  {
    title: "Teach",
    text: "Upload a brand document. Brand Brain drafts the voice, audience and pillars — you approve the version that matters.",
  },
  {
    title: "Create",
    text: "Campaign Studio and Content Studio turn approved brand context into ideas, scripts, images and video.",
  },
  {
    title: "Review",
    text: "Brand Guardian checks every piece against the rules. Approval Center is the only door to publishing.",
  },
  {
    title: "Learn",
    text: "Analytics compares real results against a baseline and proposes lessons, which you approve before they change anything.",
  },
];

const NAV_LINKS = [
  { label: "Platform", href: "#platform" },
  { label: "Agent team", href: "#agents" },
  { label: "How it works", href: "#how-it-works" },
];

function NavBar() {
  return (
    <header className="sticky top-0 z-50 border-b border-border/60 bg-background/70 backdrop-blur-lg supports-backdrop-filter:bg-background/60">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
        <Link href="/" className="flex items-center gap-2">
          <span className="relative flex size-8 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-primary to-[oklch(0.55_0.2_305)] text-primary-foreground shadow-md shadow-primary/40">
            <span
              className="absolute inset-0 -z-10 rounded-lg bg-primary/50 blur-md"
              aria-hidden="true"
            />
            <LogoMark className="size-4.5" />
          </span>
          <span className="text-base font-semibold tracking-tight">CreatorOS</span>
        </Link>
        <nav aria-label="Sections" className="hidden items-center gap-6 md:flex">
          {NAV_LINKS.map((link) => (
            <a
              key={link.href}
              href={link.href}
              className="text-sm font-medium text-muted-foreground transition-colors hover:text-foreground"
            >
              {link.label}
            </a>
          ))}
        </nav>
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="sm" render={<Link href="/sign-in" />}>
            Sign in
          </Button>
          <Button
            size="sm"
            render={<Link href="/sign-up" />}
            className="bg-gradient-to-r from-primary to-[oklch(0.58_0.2_305)] text-primary-foreground shadow-md shadow-primary/30 transition-transform hover:scale-[1.03] hover:from-primary hover:to-[oklch(0.58_0.2_305)]"
          >
            Start free
          </Button>
        </div>
      </div>
    </header>
  );
}

function AgentOrbit() {
  return (
    <div className="orbit-scene mx-auto flex h-[320px] w-full max-w-sm items-center justify-center sm:h-[360px]">
      <div
        className="glow-blob size-52 bg-primary"
        style={{ top: "12%", left: "8%" }}
        aria-hidden="true"
      />
      <div
        className="glow-blob size-52"
        style={{ bottom: "8%", right: "4%", background: "oklch(0.68 0.19 350)" }}
        aria-hidden="true"
      />
      <div className="relative z-[2] flex size-20 items-center justify-center rounded-full bg-gradient-to-br from-primary to-[oklch(0.55_0.2_305)] text-primary-foreground shadow-lg shadow-primary/30">
        <LogoMark className="size-9" />
      </div>
      {ORBIT_AGENTS.map((agent, index) => (
        <div
          key={agent.label}
          className="orbit-node"
          style={{ animationDelay: `-${(18 / ORBIT_AGENTS.length) * index}s` }}
        >
          <div
            className="flex flex-col items-center gap-1 rounded-xl border border-border/60 bg-card px-2.5 py-2 text-center shadow-sm"
            style={{
              boxShadow: `0 8px 20px -10px ${agent.color}`,
            }}
          >
            <agent.Icon className="size-4" style={{ color: agent.color }} aria-hidden="true" />
            <span className="text-[0.65rem] font-medium whitespace-nowrap">{agent.label}</span>
          </div>
        </div>
      ))}
    </div>
  );
}

function Hero() {
  return (
    <section className="relative overflow-hidden">
      <div className="glow-blob size-96 bg-primary" style={{ top: "-10%", left: "-5%" }} aria-hidden="true" />
      <div
        className="glow-blob size-96"
        style={{ top: "5%", right: "-10%", background: "oklch(0.68 0.19 350)" }}
        aria-hidden="true"
      />
      <div className="relative mx-auto max-w-6xl px-4 pt-14 pb-16 sm:px-6 sm:pt-20 sm:pb-24 lg:px-8">
        <div className="grid gap-12 lg:grid-cols-2 lg:items-center lg:gap-16">
          <div>
            <Badge variant="secondary" className="mb-5">
              Built for agencies managing many client brands
            </Badge>
            <h1 className="text-4xl font-semibold tracking-tight text-balance sm:text-5xl">
              The AI marketing team that{" "}
              <span className="bg-gradient-to-r from-primary via-[oklch(0.6_0.19_300)] to-[oklch(0.65_0.2_350)] bg-clip-text text-transparent">
                never publishes without you
              </span>
              .
            </h1>
            <p className="mt-5 max-w-lg text-lg text-muted-foreground">
              CreatorOS remembers every client&apos;s voice, drafts campaigns and content with a
              fixed team of agents, and checks its own work — but nothing goes out the door until
              a human approves it.
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-3">
              <Button size="lg" render={<Link href="/sign-up" />}>
                Start free
              </Button>
              <Button variant="outline" size="lg" render={<Link href="/sign-in" />}>
                Sign in
              </Button>
            </div>
          </div>
          <AgentOrbit />
        </div>
      </div>
    </section>
  );
}

function Trust() {
  return (
    <section id="platform" className="scroll-mt-20 border-t border-border/60 bg-muted/30">
      <div className="mx-auto grid max-w-6xl gap-8 px-4 py-16 sm:grid-cols-3 sm:px-6 lg:px-8">
        {TRUST.map(({ title, text, Icon }) => (
          <div key={title}>
            <Icon className="size-5 text-primary" aria-hidden="true" />
            <h3 className="mt-3 font-medium">{title}</h3>
            <p className="mt-1 text-sm text-muted-foreground">{text}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

function AgentTeam() {
  return (
    <section id="agents" className="mx-auto max-w-6xl scroll-mt-20 px-4 py-16 sm:px-6 lg:px-8">
      <div className="max-w-2xl">
        <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">Your AI team</h2>
        <p className="mt-2 text-muted-foreground">
          Each agent has one job. They run in a fixed order, and people approve the results.
        </p>
      </div>
      <div className="mt-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {AGENTS.map(({ name, job, Icon }) => (
          <Card key={name} size="sm">
            <CardContent className="space-y-2">
              <Icon className="size-5 text-primary" aria-hidden="true" />
              <p className="text-sm font-medium">{name}</p>
              <p className="text-sm text-muted-foreground">{job}</p>
            </CardContent>
          </Card>
        ))}
      </div>
    </section>
  );
}

function HowItWorks() {
  return (
    <section id="how-it-works" className="scroll-mt-20 border-t border-border/60 bg-muted/30">
      <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6 lg:px-8">
        <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">How it works</h2>
        <div className="mt-8 grid gap-8 sm:grid-cols-2 lg:grid-cols-4">
          {HOW.map((step, index) => (
            <div key={step.title}>
              <span className="text-sm font-medium text-primary">{String(index + 1).padStart(2, "0")}</span>
              <h3 className="mt-2 font-medium">{step.title}</h3>
              <p className="mt-1 text-sm text-muted-foreground">{step.text}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function FinalCta() {
  return (
    <section className="mx-auto max-w-6xl px-4 py-20 text-center sm:px-6 lg:px-8">
      <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">
        Run your agency with an AI team that shows its work.
      </h2>
      <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
        <Button size="lg" render={<Link href="/sign-up" />}>
          Start free
        </Button>
        <Button variant="outline" size="lg" render={<Link href="/sign-in" />}>
          Sign in
        </Button>
      </div>
    </section>
  );
}

function Footer() {
  return (
    <footer className="border-t border-border/60">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-8 text-sm text-muted-foreground sm:px-6 lg:px-8">
        <Logo className="text-sm text-foreground" />
        <p>Built for agencies managing many client brands.</p>
      </div>
    </footer>
  );
}

export function LandingPage() {
  return (
    <div className="min-h-screen">
      <NavBar />
      <main>
        <Hero />
        <Trust />
        <AgentTeam />
        <HowItWorks />
        <FinalCta />
      </main>
      <Footer />
    </div>
  );
}
