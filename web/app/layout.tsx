import "./globals.css";
import { ClerkProvider } from "@clerk/nextjs";

export const metadata = { title: "OneLive" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  // ClerkProvider wraps the whole app so both the ops console and the gated
  // consumer feed share one auth context; the fail-closed allowlist check
  // itself lives in middleware.ts (layer 1) and api/clerk_auth.py (layer 2).
  return (
    <ClerkProvider>
      <html lang="en">
        <body>
          <div className="container">{children}</div>
        </body>
      </html>
    </ClerkProvider>
  );
}
