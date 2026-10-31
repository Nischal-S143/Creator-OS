import { CheckIcon } from "lucide-react";
import { notFound } from "next/navigation";

import { PageHeader } from "@/components/page-header";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { WireframePreview } from "@/components/wireframes";
import { findSection } from "@/lib/sections";

export async function generateMetadata({ params }: { params: Promise<{ section: string }> }) {
  const section = findSection((await params).section);
  return { title: section ? `${section.title} · CreatorOS` : "CreatorOS" };
}

export default async function PlannedSectionPage({
  params,
}: {
  params: Promise<{ section: string }>;
}) {
  const section = findSection((await params).section);
  if (!section) notFound();

  return (
    <>
      <PageHeader
        title={section.title}
        description={section.description}
        actions={<Badge variant="secondary">Coming in {section.phase}</Badge>}
      />
      <div className="grid gap-4 lg:grid-cols-5">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>What you will do here</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-sm">
            <ul className="space-y-2">
              {section.capabilities.map((capability) => (
                <li key={capability} className="flex gap-2">
                  <CheckIcon className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden="true" />
                  <span>{capability}</span>
                </li>
              ))}
            </ul>
            {section.needs ? (
              <p className="border-t pt-3 text-muted-foreground">
                <span className="font-medium text-foreground">Needs: </span>
                {section.needs}
              </p>
            ) : null}
          </CardContent>
        </Card>
        <Card className="lg:col-span-3">
          <CardHeader>
            <CardTitle>Planned layout</CardTitle>
          </CardHeader>
          <CardContent>
            <WireframePreview kind={section.wireframe} />
            <p className="mt-4 text-xs text-muted-foreground">
              An outline only. This section is not built yet and shows no data.
            </p>
          </CardContent>
        </Card>
      </div>
    </>
  );
}
