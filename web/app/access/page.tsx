import { SignedIn, SignedOut, SignInButton, SignOutButton } from "@clerk/nextjs";
import { BrandMark } from "../../components/BrandMark";
import { authProviderActive } from "../../lib/auth";

// Not prerendered at build — this screen uses Clerk components, which need the
// Clerk key at render. When no provider is configured we render the branded
// shell WITHOUT any Clerk components (they would throw with no ClerkProvider),
// so a stray visit in a non-Clerk deployment degrades gracefully.
export const dynamic = "force-dynamic";

export const metadata = {
  title: "1Live — Private preview",
  description: "1Live is in a private preview. Access is limited to an invited list.",
};

// Shown to signed-out visitors and to authenticated-but-not-allowlisted users
// (the middleware redirects the latter here — they are never let through). This
// is a designed, on-brand screen, not a stub.
export default function AccessPage() {
  const clerk = authProviderActive();
  return (
    <main style={styles.wrap}>
      <div style={styles.card}>
        <div style={styles.brand}>
          <span style={styles.mark}>
            <BrandMark size={30} />
          </span>
          <span style={styles.brandName}>
            One<b>Live</b>
          </span>
        </div>

        <p style={styles.kicker}>Private preview</p>
        <h1 style={styles.title}>You&rsquo;re a little early.</h1>
        <p style={styles.body}>
          1Live is Austin&rsquo;s trust-first guide to live music, art, food, and
          culture. We&rsquo;re opening it up to a small, invited group first while we
          get the verification right. Access is limited to an allowlist during the
          preview.
        </p>

        {clerk ? (
          <>
            <SignedOut>
              <p style={styles.body}>
                If you&rsquo;ve been invited, sign in with the email on your invitation.
              </p>
              <div style={styles.actions}>
                <SignInButton mode="modal">
                  <button style={styles.primary} data-testid="button-signin">Sign in</button>
                </SignInButton>
              </div>
            </SignedOut>

            <SignedIn>
              <p style={styles.body}>
                You&rsquo;re signed in, but this account isn&rsquo;t on the preview list
                yet. If you think that&rsquo;s a mistake, reach out to the person who
                invited you &mdash; or sign out and try the invited email.
              </p>
              <div style={styles.actions}>
                <SignOutButton>
                  <button style={styles.secondary} data-testid="button-signout">Sign out</button>
                </SignOutButton>
              </div>
            </SignedIn>
          </>
        ) : (
          <p style={styles.body}>
            Invitations open soon. Check back with the person who invited you.
          </p>
        )}

        <p style={styles.footnote}>
          Want in? Ask your host for an invite &mdash; we&rsquo;re expanding the preview
          steadily.
        </p>
      </div>
    </main>
  );
}

const styles: Record<string, React.CSSProperties> = {
  wrap: {
    minHeight: "70vh",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    padding: "24px",
  },
  card: {
    maxWidth: 520,
    width: "100%",
    background: "#0f1115",
    color: "#f4f4f5",
    border: "1px solid #23262d",
    borderRadius: 18,
    padding: "36px 32px",
    boxShadow: "0 20px 60px rgba(0,0,0,0.35)",
  },
  brand: { display: "flex", alignItems: "center", gap: 10, color: "#f4f4f5" },
  mark: { display: "inline-flex", color: "#f4f4f5" },
  brandName: { fontSize: 20, letterSpacing: "-0.01em" },
  kicker: {
    marginTop: 26,
    marginBottom: 6,
    color: "#ffb23e",
    fontSize: 13,
    fontWeight: 600,
    textTransform: "uppercase",
    letterSpacing: "0.08em",
  },
  title: { margin: "0 0 12px", fontSize: 28, fontWeight: 700, lineHeight: 1.15 },
  body: { margin: "0 0 14px", fontSize: 15, lineHeight: 1.6, color: "#c9cbd1" },
  actions: { display: "flex", gap: 12, marginTop: 8, marginBottom: 6 },
  primary: {
    padding: "11px 18px",
    borderRadius: 12,
    border: "1px solid #ffb23e",
    background: "#ffb23e",
    color: "#1a1205",
    fontWeight: 600,
    cursor: "pointer",
  },
  secondary: {
    padding: "11px 18px",
    borderRadius: 12,
    border: "1px solid #3a3f49",
    background: "transparent",
    color: "#f4f4f5",
    fontWeight: 600,
    cursor: "pointer",
  },
  footnote: { marginTop: 22, fontSize: 13, color: "#8b8f99" },
};
