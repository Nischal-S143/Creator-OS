import { ClientPicker } from "@/components/client-picker";
import { PageHeader } from "@/components/page-header";

export const metadata = { title: "Strategy Comparison · CreatorOS" };

export default function SimulatorPage() {
  return (
    <>
      <PageHeader
        title="Strategy Comparison"
        description="Choose a client, then open a campaign to compare strategies before production."
      />
      <ClientPicker tab="campaigns" />
    </>
  );
}
