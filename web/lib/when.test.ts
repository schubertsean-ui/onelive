import { describe, expect, it } from "vitest";
import { isDateOnlyStart, startDate, startTime } from "./when";

describe("1Live when = date + optional time", () => {
  it("keeps YYYY-MM-DD as that calendar day", () => {
    expect(startDate("2026-09-09")).toBe("2026-09-09");
    expect(startTime("2026-09-09")).toBeNull();
    expect(isDateOnlyStart("2026-09-09")).toBe(true);
  });

  it("UTC midnight does not roll the day back", () => {
    expect(startDate("2026-09-09T00:00:00Z")).toBe("2026-09-09");
    expect(startTime("2026-09-09T00:00:00Z")).toBeNull();
  });

  it("printed clock stays a time", () => {
    expect(startDate("2026-09-09T20:30:00-05:00")).toBe("2026-09-09");
    expect(startTime("2026-09-09T20:30:00-05:00")).toBe("20:30");
  });
});
