import { AuthForm } from "@/components/auth-form";

export const metadata = { title: "Sign in · CreatorOS" };
export const dynamic = "force-dynamic";

export default function SignInPage() {
  return <AuthForm mode="sign-in" />;
}
