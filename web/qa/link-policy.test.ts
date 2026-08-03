// Nav-canon §13.1 as a mechanical check over the /tonight sources: internal
// navigation never opens a new tab; every new-tab link is external AND carries
// rel="noopener noreferrer"; the TERMINAL ticket handoff is same-tab (§8).
// Source-level on purpose: it fails the moment a diff re-introduces the old
// blanket target="_blank" pattern, with the offending file:line named.
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

  it("the terminal ticket handoff is SAME-TAB and labeled (never a stranded tab)", () => {
    // The two ticket affordances (lens .lbtn on tix; detail .dtix) must not
    // carry target=_blank, and must announce the external destination.
    const feedApp = files.find((f) => f.path.endsWith("FeedApp.tsx"));
    const detail = files.find((f) => f.path.endsWith(join("[id]", "page.tsx")));
    expect(feedApp && detail).toBeTruthy();
    for (const { src, path } of [feedApp!, detail!]) {
      const ticketTags = [...src.matchAll(/<a\b[^>]*className="(?:lbtn|dtix)"[^>]*>/gs)]
        .map((m) => m[0])
        .filter((tag) => tag.includes("{tix}") || tag.includes("href={tix}"));
      expect(ticketTags.length, `${path}: expected a ticket anchor`).toBeGreaterThan(0);
      for (const tag of ticketTags) {
        expect(tag, `${path}: ticket handoff must be same-tab (§8 terminal row)`).not.toContain('target="_blank"');
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
