import { AuthForm } from "@/components/auth-form";

export const metadata = { title: "Sign in · CreatorOS" };

export default function SignInPage() {
  return <AuthForm mode="sign-in" />;
}
