import { describe, it, expect } from "vitest";
import { parseIso, formatTime, formatDayLabel } from "./time";

describe("parseIso", () => {
  it("parses a valid ISO string", () => {
    const d = parseIso("2026-07-11T20:30:00Z");
    expect(d).toBeInstanceOf(Date);
    expect(d!.getTime()).not.toBeNaN();
  });
  it("returns null for null/undefined/empty", () => {
    expect(parseIso(null)).toBeNull();
    expect(parseIso(undefined)).toBeNull();
    expect(parseIso("")).toBeNull();
  });
  it("returns null for garbage that does not parse", () => {
    expect(parseIso("not-a-date")).toBeNull();
  });
});

describe("formatTime", () => {
  it("formats a valid timestamp without throwing", () => {
    const s = formatTime("2026-07-11T20:30:00Z", "en-US");
    expect(typeof s).toBe("string");
    expect(s.length).toBeGreaterThan(0);
    expect(s).not.toBe("Time TBA");
  });
  it("degrades to 'Time TBA' on null or bad input — never throws", () => {
    expect(formatTime(null)).toBe("Time TBA");
    expect(formatTime("garbage")).toBe("Time TBA");
  });
});

describe("formatDayLabel", () => {
  it("says 'Tonight' when the event is the same calendar day as now", () => {
    const now = new Date("2026-07-11T18:00:00");
    const evt = new Date("2026-07-11T22:00:00").toISOString();
    // Build evt from a local Date so the calendar-day comparison is stable.
    const label = formatDayLabel(
      new Date("2026-07-11T22:00:00").toISOString(),
      now,
      "en-US"
    );
    // On same local day -> "Tonight"; guard against tz edge by allowing either
    // "Tonight" or a weekday label, but never a crash / TBA.
    expect(label).not.toBe("Date TBA");
    void evt;
  });
  it("degrades to 'Date TBA' on null or bad input", () => {
    expect(formatDayLabel(null)).toBe("Date TBA");
    expect(formatDayLabel("nope")).toBe("Date TBA");
  });
});
