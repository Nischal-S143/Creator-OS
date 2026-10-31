import { ClientPicker } from "@/components/client-picker";
import { PageHeader } from "@/components/page-header";

export const metadata = { title: "Audience Intelligence · CreatorOS" };

export default function AudiencePage() {
  return (
    <>
      <PageHeader
        title="Audience Intelligence"
        description="Choose a client to turn real audience comments into campaign opportunities."
      />
      <ClientPicker tab="audience" />
    </>
  );
}
