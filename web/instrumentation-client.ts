/**
 * Sentinel minimum (Session Contract #1): browser-side Sentry init behind
 * NEXT_PUBLIC_SENTRY_DSN. Next.js 15 loads this file natively in the client
 * bundle. With no DSN set, Sentry.init is a documented no-op, so the public
 * bundle carries no active telemetry until the founder mints a DSN.
 */
import * as Sentry from "@sentry/nextjs";

const dsn = process.env.NEXT_PUBLIC_SENTRY_DSN;
if (dsn) {
  Sentry.init({
    dsn,
    environment: process.env.NEXT_PUBLIC_ONELIVE_ENV ?? "development",
    // Error monitoring only for now — see instrumentation.ts.
    tracesSampleRate: 0,
  });
  Sentry.setTag("surface", "web-client");
}
