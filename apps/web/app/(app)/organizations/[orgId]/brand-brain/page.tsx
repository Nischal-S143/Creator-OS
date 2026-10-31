import { ClientPicker } from "@/components/client-picker";
import { PageHeader } from "@/components/page-header";

export const metadata = { title: "Brand Brain · CreatorOS" };

export default function BrandBrainPage() {
  return (
    <>
      <PageHeader
        title="Brand Brain"
        description="Choose a client to manage its guidelines and approved brand profile."
      />
      <ClientPicker tab="brain" />
    </>
  );
}
