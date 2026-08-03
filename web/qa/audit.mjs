// Mechanical WCAG 2.2 AA + lab-CWV audit of /tonight (UI Canon §1.8 + §1.3;
// Master Design Brief: WCAG 2.2 AA, "loads in under 2 seconds", LCP ≤ 2.5s).
//
// Runs against the SYNTHETIC QA fixture boot (same server tools/visual_check.sh
// uses), so results are deterministic and no real entity is audited. Two legs:
//
//   1. ACCESSIBILITY (blocking): axe-core with the WCAG 2.0/2.1/2.2 A+AA tag
//      set on each page — any violation exits 1 with the nodes printed.
//      Honest scope: axe automates the machine-checkable subset of WCAG (it
//      finds real violations; a clean run is NOT a certification — keyboard
//      and screen-reader passes remain human work, tracked in the audit doc).
//
//   2. LAB LCP (blocking, lab-scoped): largest-contentful-paint measured under
//      pinned throttling (4× CPU slowdown + ~1.6 Mbps / 150 ms RTT via CDP)
//      against the LOCAL production boot. This is a LAB budget check — it
//      catches render-cost regressions; it does not measure real-user field
//      CWV, which needs the deployed site + analytics (founder-gated).
//
// Usage: node qa/audit.mjs --base http://localhost:PORT [--lcp-budget 2000]
// Requires: playwright-core (pinned 1.56.0) + a Chromium binary
// (ONELIVE_CHROMIUM, default /opt/pw-browsers/chromium — build 1194).
import { chromium } from "playwright-core";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const AXE_SRC = readFileSync(require.resolve("axe-core/axe.min.js"), "utf8");

const args = process.argv.slice(2);
function arg(name, fallback) {
  const i = args.indexOf(name);
  return i >= 0 && args[i + 1] ? args[i + 1] : fallback;
}
const BASE = arg("--base", "");
const LCP_BUDGET_MS = Number(arg("--lcp-budget", "2000"));
if (!BASE) {
  console.error("audit: --base http://localhost:PORT is required");
  process.exit(2);
}

// Same surfaces the visual baselines pin. Mobile-first; the desktop feed once.
const PAGES = [
  { name: "feed-mobile", path: "/tonight", viewport: { width: 390, height: 844 } },
  { name: "feed-desktop", path: "/tonight", viewport: { width: 1280, height: 900 } },
  { name: "detail-disputed", path: "/tonight/qa-4", viewport: { width: 390, height: 844 } },
  { name: "detail-cancelled", path: "/tonight/qa-9", viewport: { width: 390, height: 844 } },
];

// The full machine-checkable WCAG A/AA rule surface, 2.0 through 2.2.
const AXE_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

const executablePath = process.env.ONELIVE_CHROMIUM || "/opt/pw-browsers/chromium";
// --no-sandbox + --disable-dev-shm-usage everywhere this runs: required as
// root (this sandbox) AND on ubuntu-24 GitHub runners (AppArmor blocks the
// unprivileged-userns sandbox → Chromium aborts; small /dev/shm crashes the
// renderer). Safe for THIS use: a single-use machine auditing only our own
// localhost fixture pages.
const launchArgs = ["--no-sandbox", "--disable-dev-shm-usage"];

let failed = false;
const browser = await chromium.launch({ executablePath, args: launchArgs });
try {
  // ── Self-falsification check (§9.6: a gate that cannot fail proves
  // nothing): axe must flag a deliberately-broken page before any real result
  // is trusted. If it reports the bad page clean, the audit itself is broken.
  {
    const ctx = await browser.newContext();
    const pg = await ctx.newPage();
    await pg.setContent(
      `<main><img src="x.png"><p style="color:#777;background:#888">low contrast</p>
       <input type="text"></main>`,
    );
    await pg.evaluate(AXE_SRC);
    const bad = await pg.evaluate(
      (tags) => window.axe.run(document, { runOnly: { type: "tag", values: tags } }),
      AXE_TAGS,
    );
    await ctx.close();
    if (!bad.violations.length) {
      console.error("[audit] HARD FAIL: axe reported a known-broken page as clean — the audit cannot be trusted");
      process.exit(2);
    }
    console.log(`[audit] self-check OK — axe flags the planted-broken page (${bad.violations.length} violation(s))`);
  }

  for (const p of PAGES) {
    const context = await browser.newContext({
      viewport: p.viewport,
      timezoneId: "America/Chicago",
    });
    const page = await context.newPage();
    const url = `${BASE}${p.path}`;

    // ── Leg 1: axe (unthrottled — rules, not timing) ──────────────────────
    await page.goto(url, { waitUntil: "networkidle" });
    await page.evaluate(AXE_SRC);
    const axeResult = await page.evaluate(
      (tags) => window.axe.run(document, { runOnly: { type: "tag", values: tags } }),
      AXE_TAGS,
    );
    if (axeResult.violations.length) {
      failed = true;
      console.error(`\n[audit] A11Y FAIL ${p.name} (${url}) — ${axeResult.violations.length} violation(s):`);
      for (const v of axeResult.violations) {
        console.error(`  · ${v.id} [${v.impact}] ${v.help} — ${v.helpUrl}`);
        for (const n of v.nodes.slice(0, 5)) {
          console.error(`      ${n.target.join(" ")}`);
        }
        if (v.nodes.length > 5) console.error(`      … and ${v.nodes.length - 5} more node(s)`);
      }
    } else {
      console.log(`[audit] a11y PASS ${p.name} — 0 violations (tags: ${AXE_TAGS.join(",")}; ${axeResult.passes.length} rules passed)`);
    }

    // The slide-out lens (role=dialog) is the richest a11y surface — audit it
    // OPEN on the mobile feed, not just the resting card state.
    if (p.name === "feed-mobile") {
      await page.click(".z-artist");
      await page.waitForSelector(".lensroot .sheet", { timeout: 5000 });
      const lensAxe = await page.evaluate(
        (tags) => window.axe.run(document, { runOnly: { type: "tag", values: tags } }),
        AXE_TAGS,
      );
      if (lensAxe.violations.length) {
        failed = true;
        console.error(`\n[audit] A11Y FAIL ${p.name}+lens-open — ${lensAxe.violations.length} violation(s):`);
        for (const v of lensAxe.violations) {
          console.error(`  · ${v.id} [${v.impact}] ${v.help} — ${v.helpUrl}`);
          for (const n of v.nodes.slice(0, 5)) console.error(`      ${n.target.join(" ")}`);
        }
      } else {
        console.log(`[audit] a11y PASS ${p.name}+lens-open — 0 violations`);
      }
      await page.keyboard.press("Escape");
    }

    // ── Leg 2: lab LCP under pinned throttling ────────────────────────────
    const cdp = await context.newCDPSession(page);
    await cdp.send("Emulation.setCPUThrottlingRate", { rate: 4 });
    await cdp.send("Network.enable");
    await cdp.send("Network.emulateNetworkConditions", {
      offline: false,
      latency: 150,
      downloadThroughput: (1.6 * 1024 * 1024) / 8,
      uploadThroughput: (0.75 * 1024 * 1024) / 8,
    });
    await page.goto(url, { waitUntil: "load" });
    const lcpMs = await page.evaluate(
      () =>
        new Promise((resolve) => {
          let last = 0;
          new PerformanceObserver((list) => {
            for (const e of list.getEntries()) last = e.startTime;
          }).observe({ type: "largest-contentful-paint", buffered: true });
          // LCP finalizes on interaction/lifecycle; sample after settle.
          setTimeout(() => resolve(Math.round(last)), 1500);
        }),
    );
    if (!lcpMs) {
      failed = true;
      console.error(`[audit] LCP FAIL ${p.name} — no largest-contentful-paint entry recorded`);
    } else if (lcpMs > LCP_BUDGET_MS) {
      failed = true;
      console.error(`[audit] LCP FAIL ${p.name} — ${lcpMs}ms > ${LCP_BUDGET_MS}ms lab budget (4× CPU, 1.6Mbps/150ms)`);
    } else {
      console.log(`[audit] LCP PASS ${p.name} — ${lcpMs}ms ≤ ${LCP_BUDGET_MS}ms lab budget (4× CPU, 1.6Mbps/150ms)`);
    }
    await context.close();
  }
} finally {
  await browser.close();
}

if (failed) {
  console.error("\n[audit] RESULT: FAIL");
  process.exit(1);
}
console.log("\n[audit] RESULT: PASS (a11y machine-checkable subset + lab LCP budget)");
