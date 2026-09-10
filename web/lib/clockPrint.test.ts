import { describe, it, expect } from "vitest";
import { printWhen } from "./clockPrint";

describe("printWhen — no invented hour", () => {
  it("date-only prints the day, not 7:00 PM", () => {
    expect(printWhen("2026-09-10")).toBe("Thu, Sep 10");
    expect(printWhen("2026-09-10T00:00:00Z")).toBe("Thu, Sep 10");
  });

  it("printed hour stays", () => {
    expect(printWhen("2026-09-10T21:00:00-05:00")).toBe("Thu, Sep 10, 9 PM");
  });

  it("missing is Date TBA", () => {
    expect(printWhen(null)).toBe("Date TBA");
    expect(printWhen("")).toBe("Date TBA");
  });
});
