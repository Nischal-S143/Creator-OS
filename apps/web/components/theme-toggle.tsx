"use client";

import { MonitorIcon, MoonIcon, SunIcon } from "lucide-react";
import { useTheme } from "next-themes";

import { useHydrated } from "@/lib/use-hydrated";
import { cn } from "@/lib/utils";

const OPTIONS = [
  { value: "light", label: "Light theme", Icon: SunIcon },
  { value: "dark", label: "Dark theme", Icon: MoonIcon },
  { value: "system", label: "Match system theme", Icon: MonitorIcon },
];

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  const hydrated = useHydrated();
  return (
    <div role="group" aria-label="Theme" className="inline-flex rounded-lg border bg-background p-0.5">
      {OPTIONS.map(({ value, label, Icon }) => (
        <button
          key={value}
          type="button"
          aria-label={label}
          title={label}
          aria-pressed={hydrated && theme === value}
          onClick={() => setTheme(value)}
          className={cn(
            "rounded-md p-1.5 text-muted-foreground outline-none hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring",
            hydrated && theme === value && "bg-accent text-accent-foreground",
          )}
        >
          <Icon className="size-3.5" />
        </button>
      ))}
    </div>
  );
}
