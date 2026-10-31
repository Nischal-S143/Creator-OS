"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";

import { Logo } from "@/components/logo";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError, request } from "@/lib/api";
import { useHydrated } from "@/lib/use-hydrated";

export function AuthForm({ mode }: { mode: "sign-in" | "sign-up" }) {
  const isSignUp = mode === "sign-up";
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const hydrated = useHydrated();

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await request(`/api/session/${isSignUp ? "signup" : "login"}`, {
        method: "POST",
        body: { email, password },
      });
      window.location.assign("/dashboard");
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Something went wrong.");
      setBusy(false);
    }
  }

  return (
    <div className="w-full max-w-sm space-y-6">
      <div className="space-y-2">
        <Logo className="lg:hidden" />
        <h1 className="text-2xl font-semibold tracking-tight">
          {isSignUp ? "Create your account" : "Welcome back"}
        </h1>
        <p className="text-sm text-muted-foreground">
          {isSignUp
            ? "Set up your agency workspace in a minute."
            : "Sign in to your agency workspace."}
        </p>
      </div>
      <form onSubmit={submit} className="space-y-4">
        {error ? (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        ) : null}
        <div className="space-y-2">
          <Label htmlFor="email">Email</Label>
          <Input
            id="email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="password">Password</Label>
          <Input
            id="password"
            type="password"
            autoComplete={isSignUp ? "new-password" : "current-password"}
            required
            minLength={isSignUp ? 10 : undefined}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
          {isSignUp ? (
            <p className="text-xs text-muted-foreground">Use at least 10 characters.</p>
          ) : null}
        </div>
        <Button type="submit" className="w-full" disabled={busy || !hydrated}>
          {busy ? "Please wait…" : isSignUp ? "Create account" : "Sign in"}
        </Button>
      </form>
      <p className="text-center text-sm text-muted-foreground">
        {isSignUp ? "Already have an account? " : "New to CreatorOS? "}
        <Link
          href={isSignUp ? "/sign-in" : "/sign-up"}
          className="font-medium text-foreground underline underline-offset-4"
        >
          {isSignUp ? "Sign in" : "Create an account"}
        </Link>
      </p>
    </div>
  );
}
