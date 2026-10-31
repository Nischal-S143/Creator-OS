"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";
import { toast } from "sonner";

import { useOrg } from "@/components/org-shell";
import { PageHeader } from "@/components/page-header";
import { EmptyState, ErrorState, LoadingRows } from "@/components/states";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError, api, can, slugify, useResource, type Brand, type Page } from "@/lib/api";

export default function ClientsPage() {
  const organization = useOrg();
  const base = `/organizations/${organization.id}`;
  const allowed = can.viewBrands(organization.role);
  const path = `${base}/brands`;
  const { data, error, loading, reload } = useResource<Page<Brand>>(`${path}?limit=100`);
  const [name, setName] = useState("");
  const [industry, setIndustry] = useState("");
  const [busy, setBusy] = useState(false);
  const slug = slugify(name);

  async function create(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    try {
      await api<Brand>(path, {
        method: "POST",
        body: { name, slug, industry: industry.trim() || null },
      });
      toast.success(`Added ${name}`);
      setName("");
      setIndustry("");
      reload();
    } catch (caught) {
      toast.error(caught instanceof ApiError ? caught.message : "Could not add the client.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <PageHeader title="Clients" description="The brands your agency manages." />
      {!allowed ? (
        <EmptyState title="No clients assigned">
          You will see clients here once they are assigned to you.
        </EmptyState>
      ) : (
        <div className="space-y-6">
          {loading ? <LoadingRows /> : null}
          {error ? <ErrorState message={error.message} onRetry={reload} /> : null}
          {data && data.items.length === 0 ? (
            <EmptyState title="No clients yet">
              {can.createBrand(organization.role)
                ? "Add your first client brand below."
                : "An owner or admin can add client brands."}
            </EmptyState>
          ) : null}
          {data && data.items.length > 0 ? (
            <div className="grid gap-4 sm:grid-cols-2">
              {data.items.map((brand) => (
                <Link
                  key={brand.id}
                  href={`${base}/brands/${brand.id}`}
                  className="rounded-xl outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  <Card className="h-full transition-colors hover:bg-muted/50">
                    <CardHeader>
                      <CardTitle className="truncate">{brand.name}</CardTitle>
                      <CardDescription className="truncate">
                        {brand.industry ?? "No industry set"}
                      </CardDescription>
                    </CardHeader>
                  </Card>
                </Link>
              ))}
            </div>
          ) : null}
          {can.createBrand(organization.role) ? (
            <Card>
              <CardHeader>
                <CardTitle>Add a client</CardTitle>
              </CardHeader>
              <CardContent>
                <form onSubmit={create} className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="brand-name">Client brand name</Label>
                    <Input
                      id="brand-name"
                      required
                      maxLength={200}
                      value={name}
                      onChange={(event) => setName(event.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="brand-industry">Industry (optional)</Label>
                    <Input
                      id="brand-industry"
                      maxLength={100}
                      value={industry}
                      onChange={(event) => setIndustry(event.target.value)}
                    />
                  </div>
                  <div className="sm:col-span-2">
                    <Button type="submit" disabled={busy || slug.length < 2}>
                      {busy ? "Adding…" : "Add client"}
                    </Button>
                  </div>
                </form>
              </CardContent>
            </Card>
          ) : null}
        </div>
      )}
    </>
  );
}
