/** Pure layout maths for the roadmap timeline (unit-tested in timeline.test.ts). */
import { daysBetween, parseDate } from "./dates";

export interface Span {
  start: string; // ISO date
  end: string;
}

export interface Scale {
  from: Date;
  to: Date;
  /** 0..100 percentage position of an ISO date, clamped. */
  x: (iso: string) => number;
  months: { iso: string; label: string; x: number; year: boolean }[];
}

export function makeScale(spans: Span[], extra: string[] = []): Scale {
  const dates = [...spans.flatMap((s) => [s.start, s.end]), ...extra].map(parseDate);
  const min = new Date(Math.min(...dates.map((d) => d.getTime())));
  const max = new Date(Math.max(...dates.map((d) => d.getTime())));
  const from = new Date(Date.UTC(min.getUTCFullYear(), min.getUTCMonth(), 1));
  const to = new Date(Date.UTC(max.getUTCFullYear(), max.getUTCMonth() + 1, 1));
  const total = Math.max(1, daysBetween(from, to));
  const x = (iso: string) => Math.min(100, Math.max(0, (daysBetween(from, parseDate(iso)) / total) * 100));
  const months: Scale["months"] = [];
  const step = total > 1100 ? 6 : total > 540 ? 3 : 1;
  for (let d = new Date(from); d < to; d = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + step, 1))) {
    const iso = d.toISOString().slice(0, 10);
    const year = d.getUTCMonth() === 0;
    months.push({
      iso,
      x: x(iso),
      year,
      label: year ? String(d.getUTCFullYear()) : d.toLocaleDateString("en-GB", { month: "short", timeZone: "UTC" }),
    });
  }
  return { from, to, x, months };
}

/** Left/width percentages for a bar between two ISO dates. */
export function bar(scale: Scale, start: string, end: string): { left: number; width: number } {
  const a = scale.x(start);
  const b = scale.x(end);
  return { left: Math.min(a, b), width: Math.max(0.6, Math.abs(b - a)) };
}

/** Parse "[cite:id]" markers into text and citation segments. */
export type Segment = { kind: "text"; text: string } | { kind: "cite"; id: string };

export function segments(text: string): Segment[] {
  const out: Segment[] = [];
  const re = /\[cite:([^\]]+)\]/g;
  let last = 0;
  for (const m of text.matchAll(re)) {
    const at = m.index ?? 0;
    if (at > last) out.push({ kind: "text", text: text.slice(last, at) });
    out.push({ kind: "cite", id: m[1].trim() });
    last = at + m[0].length;
  }
  if (last < text.length) out.push({ kind: "text", text: text.slice(last) });
  return out;
}
