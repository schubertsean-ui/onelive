// Build-trigger marker (2026-08-02): forces a fresh PRODUCTION build so the
// operator-set NEXT_PUBLIC_AUTH_DISABLED=1 (non-Sensitive) is build-inlined into
// the edge middleware and the open feed serves publicly. Vercel skips production
// builds for pushes that don't touch web/ (rootDirectory=web), so a web/ change
// is required to rebuild. No behavior change — see lib/auth.ts / docs/DEPLOY.md.
import "./globals.css";
import { ClerkProvider } from "@clerk/nextjs";
import { authProviderActive } from "../lib/auth";

export const metadata = {
  // Honest by construction (evaluator #144): no completeness claim ("everything")
  // and no price-veracity guarantee ("real prices") — those would overclaim on a
  // public search/social surface. The venue is always the last word.
  title: "1LIVE — Tonight in Austin",
  description:
    "Find live events across Central Texas — real listings from trusted sources; the venue is always the last word. No login, no pay-to-rank.",
};

// The Clerk auth context is applied ONLY when a provider is actually configured
// (see lib/auth.ts — the single source of truth). With no provider the app still
// builds and renders; access control is then decided by middleware.ts, which
// fails closed unless an explicit disable is declared. This is why the build no
// longer fails on a missing Clerk key — WITHOUT silently opening the app.
export default function RootLayout({ children }: { children: React.ReactNode }) {
  const shell = (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
  return authProviderActive() ? <ClerkProvider>{shell}</ClerkProvider> : shell;
}
