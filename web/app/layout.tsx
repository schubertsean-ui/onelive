// Build-trigger marker (2026-09-09): locale is device or search. CAPCOG is a test filter.
import "./globals.css";
import { ClerkProvider } from "@clerk/nextjs";
import { authProviderActive } from "../lib/auth";
import { SpeedInsights } from "@vercel/speed-insights/next";
import { Analytics } from "@vercel/analytics/next";

export const metadata = {
  title: "1Live — What's on",
  description:
    "What's really on — any category, any locale. Today, Tonight, a kind. Real listings. We send you to the specialist.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const shell = (
    <html lang="en">
      <body>
        {children}
        <SpeedInsights />
        <Analytics />
      </body>
    </html>
  );
  return authProviderActive() ? <ClerkProvider>{shell}</ClerkProvider> : shell;
}
