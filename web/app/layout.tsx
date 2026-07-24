import "./globals.css";
import { ClerkProvider } from "@clerk/nextjs";
import { authConfig } from "../lib/auth";

export const metadata = { title: "ONE LIVE — Tonight in Austin" };

// The auth context is applied only when the stealth gate is configured (see
// lib/auth.ts — the single source of truth). With no provider set the app still
// builds and renders on just the Supabase read key; the gate is added before any
// public go-live. This is why the build no longer fails on a missing Clerk key.
export default function RootLayout({ children }: { children: React.ReactNode }) {
  const shell = (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
  const auth = authConfig();
  return auth.enabled && auth.provider === "clerk" ? (
    <ClerkProvider>{shell}</ClerkProvider>
  ) : (
    shell
  );
}
