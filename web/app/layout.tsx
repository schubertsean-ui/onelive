import "./globals.css";
import { ClerkProvider } from "@clerk/nextjs";

export const metadata = { title: "ONE LIVE — Tonight in Austin" };

// Clerk is OPTIONAL. When NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY is set, the whole app
// is wrapped in the auth context and the stealth allowlist gate (middleware.ts)
// is active. When it is absent — e.g. an early private preview deploy that only
// carries the Supabase read key — the app still builds and renders (the Vercel
// preview URL is itself unguessable / non-indexed), and the Clerk stealth gate
// is added before any public go-live. This is why the build no longer fails on a
// missing Clerk key while we get the real-data feed in front of the founder.
const clerkEnabled = !!process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const shell = (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
  return clerkEnabled ? <ClerkProvider>{shell}</ClerkProvider> : shell;
}
