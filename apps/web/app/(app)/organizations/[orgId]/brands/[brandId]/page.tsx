"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, use, useState, type FormEvent } from "react";
import { toast } from "sonner";

import { AudienceIntelligence } from "@/components/audience-intelligence";
import { BrandBrain } from "@/components/brand-brain";
import { CampaignList } from "@/components/campaign-list";
import { MarketGaps } from "@/components/market-gaps";
import { LearningLedger } from "@/components/learning-ledger";
import { useOrg } from "@/components/org-shell";
import { PageHeader } from "@/components/page-header";
import { ErrorState, LoadingRows } from "@/components/states";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError, api, can, useResource, type Brand } from "@/lib/api";
import { cn } from "@/lib/utils";

const TABS = [
  { key: "brain", label: "Brand Brain" },
  { key: "campaigns", label: "Campaigns" },
  { key: "audience", label: "Audience" },
  { key: "lessons", label: "Lessons" },
  { key: "details", label: "Details" },
] as const;

function BrandForm({
  brand,
  path,
  editable,
  onSaved,
}: {
  brand: Brand;
  path: string;
  editable: boolean;
  onSaved: () => void;
}) {
  const [name, setName] = useState(brand.name);
  const [industry, setIndustry] = useState(brand.industry ?? "");
  const [website, setWebsite] = useState(brand.website_url ?? "");
  const [busy, setBusy] = useState(false);

  async function save(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    try {
      await api<Brand>(path, {
        method: "PATCH",
        body: { name, industry: industry.trim() || null, website_url: website.trim() || null },
      });
      toast.success("Saved");
      onSaved();
    } catch (caught) {
      toast.error(caught instanceof ApiError ? caught.message : "Could not save.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Client details</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={save} className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-2">
            <Label htmlFor="name">Name</Label>
            <Input
              id="name"
              required
              maxLength={200}
              disabled={!editable}
              value={name}
              onChange={(event) => setName(event.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="industry">Industry</Label>
            <Input
              id="industry"
              maxLength={100}
              disabled={!editable}
              value={industry}
              onChange={(event) => setIndustry(event.target.value)}
            />
          </div>
          <div className="space-y-2 sm:col-span-2">
            <Label htmlFor="website">Website</Label>
            <Input
              id="website"
              type="url"
              placeholder="https://"
              disabled={!editable}
              value={website}
              onChange={(event) => setWebsite(event.target.value)}
            />
          </div>
          {editable ? (
            <div className="sm:col-span-2">
              <Button type="submit" disabled={busy}>
                {busy ? "Saving…" : "Save changes"}
              </Button>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground sm:col-span-2">
              Your role can view this client but not change it.
            </p>
          )}
        </form>
      </CardContent>
    </Card>
  );
}

function BrandDetail({ brandId }: { brandId: string }) {
  const organization = useOrg();
  const role = organization.role;
  const clients = `/organizations/${organization.id}/clients`;
  const path = `/organizations/${organization.id}/brands/${brandId}`;
  const router = useRouter();
  const requested = useSearchParams().get("tab");
  const tab = TABS.find((item) => item.key === requested)?.key ?? "brain";
  const { data, error, loading, reload } = useResource<Brand>(path);

  if (loading) return <LoadingRows rows={2} />;
  if (error) return <ErrorState message={error.message} onRetry={reload} />;
  if (!data) return null;

  return (
    <>
      <PageHeader
        title={data.name}
        description={data.industry ?? undefined}
        back={{ href: clients, label: "All clients" }}
      />
      <nav aria-label="Client sections" className="mb-6 flex gap-1 border-b">
        {TABS.map((item) => (
          <button
            key={item.key}
            type="button"
            aria-current={tab === item.key ? "page" : undefined}
            onClick={() => router.replace(`${path}?tab=${item.key}`, { scroll: false })}
            className={cn(
              "-mb-px border-b-2 px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring",
              tab === item.key
                ? "border-primary font-medium"
                : "border-transparent text-muted-foreground hover:text-foreground",
            )}
          >
            {item.label}
          </button>
        ))}
      </nav>
      {tab === "brain" ? <BrandBrain base={path} role={role} /> : null}
      {tab === "campaigns" ? (
        <div className="space-y-6">
          <CampaignList base={path} webBase={path} role={role} />
          {can.editCampaign(role) ? <MarketGaps base={path} /> : null}
        </div>
      ) : null}
      {tab === "audience" ? <AudienceIntelligence base={path} role={role} /> : null}
      {tab === "lessons" ? <LearningLedger base={path} role={role} /> : null}
      {tab === "details" ? (
        <BrandForm brand={data} path={path} editable={can.editBrand(role)} onSaved={reload} />
      ) : null}
    </>
  );
}

export default function BrandPage({ params }: { params: Promise<{ brandId: string }> }) {
  const { brandId } = use(params);
  return (
    <Suspense fallback={<LoadingRows rows={2} />}>
      <BrandDetail brandId={brandId} />
    </Suspense>
  );
}
