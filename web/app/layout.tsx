import "./globals.css";
import { ClerkProvider } from "@clerk/nextjs";
import { authProviderActive } from "../lib/auth";

export const metadata = { title: "1LIVE — Tonight in Austin" };

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
