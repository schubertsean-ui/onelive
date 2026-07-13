/**
 * Sentinel minimum (Session Contract #1): server/edge Sentry init behind
 * SENTRY_DSN. Next.js 15 loads this file natively on server startup. With no
 * DSN set, Sentry.init is a documented no-op (the SDK disables itself), so
 * pre-launch environments and CI run with zero Sentinel configuration.
 * Mirrors worker/sentinel.py on the Python surfaces.
 */
export async function register(): Promise<void> {
  const dsn = process.env.SENTRY_DSN ?? process.env.NEXT_PUBLIC_SENTRY_DSN;
  if (!dsn) return; // no-op without a DSN — never half-configured
  const Sentry = await import("@sentry/nextjs");
  Sentry.init({
    dsn,
    environment: process.env.ONELIVE_ENV ?? "development",
    // Error monitoring only for now; tracing volume is a later, deliberate
    // (billable) decision — matches worker/sentinel.py.
    tracesSampleRate: 0,
  });
  Sentry.setTag("surface", process.env.NEXT_RUNTIME === "edge" ? "web-edge" : "web-server");
}
