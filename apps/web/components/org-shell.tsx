"use client";

import {
  BarChart3Icon,
  BrainIcon,
  BuildingIcon,
  CalendarDaysIcon,
  ClapperboardIcon,
  ClipboardCheckIcon,
  CreditCardIcon,
  FileTextIcon,
  GaugeIcon,
  LayoutDashboardIcon,
  LightbulbIcon,
  type LucideIcon,
  MenuIcon,
  MegaphoneIcon,
  MicroscopeIcon,
  NetworkIcon,
  SettingsIcon,
  Share2Icon,
  ShieldCheckIcon,
  UsersIcon,
  XIcon,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { createContext, useContext, useState } from "react";

import { signOut, useMe } from "@/components/app-shell";
import { Logo } from "@/components/logo";
import { ThemeToggle } from "@/components/theme-toggle";
import { Button } from "@/components/ui/button";
import { can, type Organization } from "@/lib/api";
import { cn } from "@/lib/utils";

type Item = { label: string; path: string; Icon: LucideIcon; planned?: boolean };

function navigation(organization: Organization): { title: string; items: Item[] }[] {
  const role = organization.role;
  const workspace: Item[] = [{ label: "Overview", path: "", Icon: LayoutDashboardIcon }];
  if (can.viewBrands(role)) workspace.push({ label: "Clients", path: "/clients", Icon: BuildingIcon });
  const create: Item[] = can.viewBrands(role)
    ? [
        { label: "Brand Brain", path: "/brand-brain", Icon: BrainIcon },
        { label: "Campaign Studio", path: "/campaigns", Icon: MegaphoneIcon },
      ]
    : [];
  const team: Item[] = can.viewMembers(role)
    ? [{ label: "Members", path: "/members", Icon: UsersIcon }]
    : [];
  return [
    { title: "Workspace", items: workspace },
    {
      title: "Plan and create",
      items: [
        ...create,
        { label: "Audience Intelligence", path: "/audience", Icon: LightbulbIcon, planned: true },
        { label: "Flight Simulator", path: "/simulator", Icon: GaugeIcon, planned: true },
        { label: "Content Studio", path: "/content-studio", Icon: FileTextIcon },
        { label: "Video Editor", path: "/video", Icon: ClapperboardIcon, planned: true },
      ],
    },
    {
      title: "Review and publish",
      items: [
        { label: "Brand Guardian", path: "/guardian", Icon: ShieldCheckIcon },
        { label: "Approval Center", path: "/approvals", Icon: ClipboardCheckIcon },
        { label: "Publishing Calendar", path: "/calendar", Icon: CalendarDaysIcon, planned: true },
        { label: "Social Accounts", path: "/social-accounts", Icon: Share2Icon, planned: true },
      ],
    },
    {
      title: "Learn",
      items: [
        { label: "Analytics", path: "/analytics", Icon: BarChart3Icon, planned: true },
        { label: "Creative Autopsy", path: "/creative-autopsy", Icon: MicroscopeIcon, planned: true },
        { label: "Agency Intelligence", path: "/intelligence", Icon: NetworkIcon, planned: true },
      ],
    },
    {
      title: "Agency",
      items: [
        ...team,
        { label: "Usage and Billing", path: "/usage", Icon: CreditCardIcon, planned: true },
        { label: "Settings", path: "/settings", Icon: SettingsIcon },
      ],
    },
  ];
}

const OrgContext = createContext<Organization | null>(null);

export function useOrg(): Organization {
  const organization = useContext(OrgContext);
  if (!organization) throw new Error("useOrg must be used inside OrgShell");
  return organization;
}

function Sidebar({ organization }: { organization: Organization }) {
  const { me } = useMe();
  const pathname = usePathname();
  const router = useRouter();
  const base = `/organizations/${organization.id}`;

  function isActive(path: string) {
    const href = `${base}${path}`;
    if (path === "") return pathname === href;
    return pathname.startsWith(href) || (path === "/clients" && pathname.startsWith(`${base}/brands`));
  }

  return (
    <div className="flex h-full flex-col">
      <div className="space-y-3 border-b border-sidebar-border p-4">
        <Link href="/dashboard" aria-label="CreatorOS, all agencies" className="block">
          <Logo />
        </Link>
        {me.organizations.length > 1 ? (
          <select
            aria-label="Switch agency"
            value={organization.id}
            onChange={(event) => router.push(`/organizations/${event.target.value}`)}
            className="h-8 w-full truncate rounded-lg border bg-background px-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            {me.organizations.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
        ) : (
          <p className="truncate text-sm font-medium">{organization.name}</p>
        )}
      </div>
      <nav aria-label="Main" className="flex-1 space-y-5 overflow-y-auto p-3">
        {navigation(organization).map((group) => (
          <div key={group.title}>
            <p className="mb-1 px-2 text-xs font-medium text-muted-foreground">{group.title}</p>
            <ul className="space-y-0.5">
              {group.items.map(({ label, path, Icon, planned }) => {
                const active = isActive(path);
                return (
                  <li key={label}>
                    <Link
                      href={`${base}${path}`}
                      aria-current={active ? "page" : undefined}
                      className={cn(
                        "flex items-center gap-2 rounded-md px-2 py-1.5 text-sm outline-none transition-colors focus-visible:ring-2 focus-visible:ring-sidebar-ring",
                        active
                          ? "bg-sidebar-accent font-medium text-sidebar-accent-foreground"
                          : "hover:bg-sidebar-accent/60",
                        planned && !active && "text-muted-foreground",
                      )}
                    >
                      <Icon className="size-4 shrink-0" aria-hidden="true" />
                      <span className="min-w-0 flex-1 truncate">{label}</span>
                      {planned ? (
                        <span className="rounded bg-muted px-1 text-[0.65rem] font-medium text-muted-foreground">
                          Coming
                        </span>
                      ) : null}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </nav>
      <div className="space-y-3 border-t border-sidebar-border p-4">
        <p className="truncate text-xs text-muted-foreground" title={me.email}>
          {me.email}
        </p>
        <div className="flex items-center justify-between gap-2">
          <ThemeToggle />
          <Button variant="outline" size="sm" onClick={signOut}>
            Sign out
          </Button>
        </div>
      </div>
    </div>
  );
}

export function OrgShell({
  organization,
  children,
}: {
  organization: Organization;
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  // Remembering where the menu was opened closes it when navigation changes the path.
  const [openedAt, setOpenedAt] = useState<string | null>(null);
  const menuOpen = openedAt === pathname;

  return (
    <OrgContext.Provider value={organization}>
      <a
        href="#main"
        className="sr-only z-50 rounded bg-background px-3 py-2 focus:not-sr-only focus:fixed focus:left-2 focus:top-2"
      >
        Skip to content
      </a>
      <div className="flex min-h-screen">
        <aside className="sticky top-0 hidden h-screen w-64 shrink-0 border-r border-sidebar-border bg-sidebar text-sidebar-foreground lg:block">
          <Sidebar organization={organization} />
        </aside>
        {menuOpen ? (
          <div
            className="fixed inset-0 z-40 lg:hidden"
            role="dialog"
            aria-modal="true"
            aria-label="Menu"
            onKeyDown={(event) => {
              if (event.key === "Escape") setOpenedAt(null);
            }}
          >
            <button
              type="button"
              aria-label="Close menu"
              tabIndex={-1}
              className="absolute inset-0 bg-black/40"
              onClick={() => setOpenedAt(null)}
            />
            <div className="absolute inset-y-0 left-0 w-72 max-w-[85vw] bg-sidebar text-sidebar-foreground shadow-xl">
              <Button
                variant="ghost"
                size="icon-sm"
                autoFocus
                aria-label="Close menu"
                className="absolute right-2 top-2 z-10"
                onClick={() => setOpenedAt(null)}
              >
                <XIcon />
              </Button>
              <Sidebar organization={organization} />
            </div>
          </div>
        ) : null}
        <div className="flex min-w-0 flex-1 flex-col">
          <div className="sticky top-0 z-30 flex h-14 items-center gap-3 border-b bg-background/95 px-4 backdrop-blur lg:hidden">
            <Button
              variant="outline"
              size="icon-sm"
              aria-label="Open menu"
              onClick={() => setOpenedAt(pathname)}
            >
              <MenuIcon />
            </Button>
            <Logo />
          </div>
          <main id="main" className="mx-auto w-full max-w-5xl flex-1 px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
            {children}
          </main>
        </div>
      </div>
    </OrgContext.Provider>
  );
}
