import { ClientPicker } from "@/components/client-picker";
import { PageHeader } from "@/components/page-header";

export const metadata = { title: "Campaign Studio · CreatorOS" };

export default function CampaignStudioPage() {
  return (
    <>
      <PageHeader
        title="Campaign Studio"
        description="Choose a client to create campaigns and generate ideas."
      />
      <ClientPicker tab="campaigns" />
    </>
  );
}
