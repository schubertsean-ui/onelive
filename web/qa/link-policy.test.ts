// Nav-canon §13.1 as a mechanical check over the /tonight sources: internal
// navigation never opens a new tab; every new-tab link is external AND carries
// rel="noopener noreferrer". The ticket handoff rule FLIPPED at founder
// direction 2026-08-05 ("external links … should never take up the entire
// screen … a user can always know where they are and easily get back to
// 1live" — decision record 2026-08-05_trust-display-quiet.md): external
// handoffs open a NEW TAB so 1live keeps its place; §8's old same-tab
// terminal rule is superseded. Source-level on purpose: it fails the moment
// a diff drifts from the ruled behavior, with the offending file:line named.
import { describe, it, expect } from "vitest";
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";

const ROOT = join(__dirname, "..", "app", "(public)", "tonight");

function tsxFiles(dir: string): string[] {
  const out: string[] = [];
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) out.push(...tsxFiles(p));
    else if (/\.tsx?$/.test(name) && !/\.test\./.test(name)) out.push(p);
  }
  return out;
}

const files = tsxFiles(ROOT).map((p) => ({ path: p, src: readFileSync(p, "utf8") }));

// A JSX opening tag that contains target="_blank" (may span lines).
const BLANK_TAG = /<a\b[^>]*target="_blank"[^>]*>/gs;

describe("link policy (nav canon §8/§13.1)", () => {
  it("scans a non-empty source tree (the test itself can fail)", () => {
    expect(files.length).toBeGreaterThan(3);
  });

  it("internal navigation never uses target=_blank (Next <Link> carries none)", () => {
    for (const f of files) {
      for (const m of f.src.matchAll(/<Link\b[^>]*>/gs)) {
        expect(m[0], `${f.path}: internal <Link> must not open a new tab`).not.toContain('target="_blank"');
      }
      for (const m of f.src.matchAll(BLANK_TAG)) {
        // A new-tab anchor must not point at an internal route.
        expect(m[0], `${f.path}: new-tab anchor on an internal href`).not.toMatch(/href="\/(?!\/)/);
      }
    }
  });

  it("every new-tab anchor carries rel=noopener noreferrer", () => {
    for (const f of files) {
      for (const m of f.src.matchAll(BLANK_TAG)) {
        expect(m[0], `${f.path}: target=_blank without rel`).toContain('rel="noopener noreferrer"');
      }
    }
  });

  it("the ticket handoff opens a NEW TAB and is labeled (founder ruling 2026-08-05 — 1live keeps its place)", () => {
    // The two ticket affordances (lens .lbtn on tix; detail .dtix) must
    // carry target=_blank + noopener, and must announce the external
    // destination. Superseded rule: §8's same-tab terminal handoff.
    const feedApp = files.find((f) => f.path.endsWith("FeedApp.tsx"));
    const detail = files.find((f) => f.path.endsWith(join("[id]", "page.tsx")));
    expect(feedApp && detail).toBeTruthy();
    for (const { src, path } of [feedApp!, detail!]) {
      const ticketTags = [...src.matchAll(/<a\b[^>]*className="(?:lbtn|dtix)"[^>]*>/gs)]
        .map((m) => m[0])
        .filter((tag) => tag.includes("{tix}") || tag.includes("href={tix}"));
      expect(ticketTags.length, `${path}: expected a ticket anchor`).toBeGreaterThan(0);
      for (const tag of ticketTags) {
        expect(tag, `${path}: ticket handoff must open a new tab (founder ruling 2026-08-05)`).toContain('target="_blank"');
        expect(tag, `${path}: new-tab handoff without rel`).toContain('rel="noopener noreferrer"');
        expect(tag, `${path}: ticket handoff must announce its destination`).toContain("externalAriaLabel");
      }
    }
  });

  it("every new-tab anchor announces itself to screen readers (aria-label via externalAriaLabel)", () => {
    for (const f of files) {
      for (const m of f.src.matchAll(BLANK_TAG)) {
        expect(m[0], `${f.path}: unannounced external link (§8: an unannounced context change is a defect)`)
          .toMatch(/aria-label=/);
      }
    }
  });
});
