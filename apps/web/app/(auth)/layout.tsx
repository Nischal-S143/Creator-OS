import { Logo } from "@/components/logo";

const STEPS = [
  { title: "Remembers", text: "Each client's voice, audience and approved decisions." },
  { title: "Creates", text: "Campaign ideas built from what each brand has approved." },
  { title: "Keeps people in control", text: "Nothing becomes brand memory without human approval." },
];

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <aside className="relative hidden flex-col justify-between overflow-hidden bg-sidebar p-10 lg:flex">
        <div className="glow-blob size-80 bg-primary" style={{ top: "-15%", left: "-10%" }} aria-hidden="true" />
        <div
          className="glow-blob size-80"
          style={{ bottom: "-10%", right: "-10%", background: "oklch(0.68 0.19 350)" }}
          aria-hidden="true"
        />
        <Logo className="relative text-lg" />
        <div className="relative max-w-md space-y-8">
          <h2 className="text-3xl font-semibold tracking-tight text-balance">
            An{" "}
            <span className="bg-gradient-to-r from-primary via-[oklch(0.6_0.19_300)] to-[oklch(0.65_0.2_350)] bg-clip-text text-transparent">
              AI marketing agency
            </span>{" "}
            that remembers, thinks, creates, validates and learns.
          </h2>
          <ul className="space-y-4">
            {STEPS.map((step) => (
              <li key={step.title}>
                <p className="font-medium">{step.title}</p>
                <p className="text-sm text-muted-foreground">{step.text}</p>
              </li>
            ))}
          </ul>
        </div>
        <p className="relative text-xs text-muted-foreground">Built for agencies managing many client brands.</p>
      </aside>
      <main className="flex items-center justify-center p-4 sm:p-8">{children}</main>
    </div>
  );
}
