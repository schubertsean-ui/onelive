import { describe, it, expect } from "vitest";
import { titleWhen, titlePlace, titleRoom, upcomingYmd } from "./titleSlots";

const NOW = Date.parse("2026-09-10T14:00:00-05:00");

describe("titleWhen — printed date only, no invented hour", () => {
  it("reads @ Venue M/D as upcoming date", () => {
    expect(titleWhen("MAX FRY + BUZZ KULL + KONTRAVOID @ Elysium 9/10", NOW)).toBe("2026-09-10");
    expect(titleWhen("LOS THUTHANAKA + special guests @ Elysium 9/11", NOW)).toBe("2026-09-11");
    expect(titleWhen("NITZER EBB + SINE + CURSE MACKEY @ Elysium 9/12", NOW)).toBe("2026-09-12");
    expect(titleWhen("ALI + PEARL & THE OYSTERS @ The 13th Floor 9/12", NOW)).toBe("2026-09-12");
  });

  it("reads at Venue on M/D", () => {
    expect(titleWhen("Live at Mohawk on 11/1", NOW)).toBe("2026-11-01");
    expect(titleWhen("Resound Presents: Kyle Gordon at 29th St Ballroom on 10/17", NOW)).toBe("2026-10-17");
  });

  it("yearless January in September is next January", () => {
    expect(upcomingYmd(1, 15, NOW)).toBe("2027-01-15");
  });

  it("no date in title stays null — no invented clock", () => {
    expect(titleWhen("Parker Jazz Club House Band", NOW)).toBeNull();
  });
});

describe("titlePlace — unused @ / at / House Band tokens", () => {
  it("reads @ Name and keeps The", () => {
    expect(titlePlace("MAX FRY + BUZZ KULL + KONTRAVOID @ Elysium 9/10")).toBe("Elysium");
    expect(titlePlace("Yappy Hour @ Cosmic Pickle")).toBe("Cosmic Pickle");
    expect(titlePlace("ALI + PEARL & THE OYSTERS @ The 13th Floor 9/12")).toBe("The 13th Floor");
  });

  it("reads at / Live at", () => {
    expect(titlePlace("Nirvani \u201cA Nirvana Tribute Experience\u201d at Haute Spot")).toBe("Haute Spot");
    expect(titlePlace("Eli Young Band Live at Haute Spot")).toBe("Haute Spot");
    expect(titlePlace("Live at Mohawk on 11/1")).toBe("Mohawk");
  });

  it("House Band titles name the club, not a room called Elysium", () => {
    expect(titlePlace("Parker Jazz Club House Band")).toBe("Parker Jazz Club");
    expect(titlePlace("Parker Jazz Club House Band (Duke Ellington tribute)")).toBe("Parker Jazz Club");
    expect(titleRoom("Parker Jazz Club House Band", "Parker Jazz Club")).toBeNull();
  });

  it("does not attach Elysium to Parker", () => {
    expect(titlePlace("MAX FRY + BUZZ KULL + KONTRAVOID @ Elysium 9/10")).toBe("Elysium");
    expect(titlePlace("MAX FRY + BUZZ KULL + KONTRAVOID @ Elysium 9/10")).not.toBe("Parker Jazz Club");
    expect(titleRoom("MAX FRY + BUZZ KULL + KONTRAVOID @ Elysium 9/10", "Parker Jazz Club")).toBe("Elysium");
  });
});
