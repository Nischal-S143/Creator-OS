"use client";

import { TrashIcon } from "lucide-react";
import Link from "next/link";
import { useState, type FormEvent } from "react";
import { toast } from "sonner";

import { useOrg } from "@/components/org-shell";
import { PageHeader } from "@/components/page-header";
import { EmptyState, ErrorState, LoadingRows } from "@/components/states";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError, api, can, slugify, useResource, type Brand, type Page } from "@/lib/api";

export default function ClientsPage() {
  const organization = useOrg();
  const base = `/organizations/${organization.id}`;
  const allowed = can.viewBrands(organization.role);
  const canDelete = can.createBrand(organization.role);
  const path = `${base}/brands`;
  const { data, error, loading, reload } = useResource<Page<Brand>>(`${path}?limit=100`);
  const [name, setName] = useState("");
  const [industry, setIndustry] = useState("");
  const [busy, setBusy] = useState(false);
  const [removing, setRemoving] = useState<Brand | null>(null);
  const slug = slugify(name);

  async function remove() {
    if (!removing) return;
    setBusy(true);
    try {
      await api(`${path}/${removing.id}`, { method: "DELETE" });
      toast.success(`Removed ${removing.name}`);
      setRemoving(null);
      reload();
    } catch (caught) {
      toast.error(caught instanceof ApiError ? caught.message : "Could not remove this client.");
    } finally {
      setBusy(false);
    }
  }

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
                <Card key={brand.id} className="relative h-full transition-colors hover:bg-muted/50">
                  <Link
                    href={`${base}/brands/${brand.id}`}
                    className="absolute inset-0 rounded-xl outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    aria-label={`Open ${brand.name}`}
                  />
                  <CardHeader className="pr-10">
                    <CardTitle className="truncate">{brand.name}</CardTitle>
                    <CardDescription className="truncate">
                      {brand.industry ?? "No industry set"}
                    </CardDescription>
                  </CardHeader>
                  {canDelete ? (
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      aria-label={`Delete ${brand.name}`}
                      className="absolute right-2 top-2 z-10 text-muted-foreground hover:text-destructive"
                      onClick={() => setRemoving(brand)}
                    >
                      <TrashIcon />
                    </Button>
                  ) : null}
                </Card>
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

      <Dialog open={removing !== null} onOpenChange={(open) => !open && setRemoving(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Remove this client?</DialogTitle>
            <DialogDescription>
              {removing?.name} will no longer appear in your client list. Its past campaigns and content
              stay on record and are not deleted.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRemoving(null)} disabled={busy}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={remove} disabled={busy}>
              {busy ? "Removing…" : "Remove client"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
