import { describe, expect, test } from "bun:test";
import { bar, makeScale, segments } from "./timeline";
import { relative, parseDate } from "./dates";

describe("timeline scale", () => {
  const scale = makeScale([{ start: "2026-10-15", end: "2027-04-01" }], ["2028-03-01"]);

  test("starts at the first month and covers the last date", () => {
    expect(scale.from.toISOString().slice(0, 10)).toBe("2026-10-01");
    expect(scale.to.toISOString().slice(0, 10)).toBe("2028-04-01");
  });

  test("positions are monotonic and clamped", () => {
    expect(scale.x("2026-10-01")).toBe(0);
    expect(scale.x("2030-01-01")).toBe(100);
    expect(scale.x("2027-01-01")).toBeLessThan(scale.x("2027-06-01"));
  });

  test("bars have a minimum visible width", () => {
    const b = bar(scale, "2027-01-01", "2027-01-01");
    expect(b.width).toBeGreaterThan(0);
  });

  test("month ticks are ordered and mark years", () => {
    const xs = scale.months.map((m) => m.x);
    expect([...xs].sort((a, b) => a - b)).toEqual(xs);
    expect(scale.months.some((m) => m.year && m.label === "2027")).toBe(true);
  });
});

describe("citation segments", () => {
  test("splits text and markers, keeping ids with spaces", () => {
    expect(segments("A [cite:ISO 24113 §6.4] b [cite:x].")).toEqual([
      { kind: "text", text: "A " },
      { kind: "cite", id: "ISO 24113 §6.4" },
      { kind: "text", text: " b " },
      { kind: "cite", id: "x" },
      { kind: "text", text: "." },
    ]);
  });
  test("text without markers is one segment", () => {
    expect(segments("plain")).toEqual([{ kind: "text", text: "plain" }]);
  });
});

describe("relative dates", () => {
  const now = parseDate("2026-10-15");
  test("future, past and today", () => {
    expect(relative("2026-10-15", now)).toBe("today");
    expect(relative("2026-10-16", now)).toBe("in 1 day");
    expect(relative("2026-11-12", now)).toBe("in 4 weeks");
    expect(relative("2026-10-01", now)).toBe("2 weeks ago");
    expect(relative("2027-10-15", now)).toBe("in 12 months");
  });
});
