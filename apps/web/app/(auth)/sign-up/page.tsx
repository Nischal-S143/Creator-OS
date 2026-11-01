import { AuthForm } from "@/components/auth-form";

export const metadata = { title: "Create account · CreatorOS" };
export const dynamic = "force-dynamic";

export default function SignUpPage() {
  return <AuthForm mode="sign-up" />;
}
