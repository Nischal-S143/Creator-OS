import { AuthForm } from "@/components/auth-form";

export const metadata = { title: "Create account · CreatorOS" };

export default function SignUpPage() {
  return <AuthForm mode="sign-up" />;
}
