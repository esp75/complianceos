const DAY = 86_400_000;

export function parseDate(iso: string): Date {
  const [y, m, d] = iso.slice(0, 10).split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d));
}

export function today(): Date {
  const n = new Date();
  return new Date(Date.UTC(n.getFullYear(), n.getMonth(), n.getDate()));
}

export function daysBetween(a: Date, b: Date): number {
  return Math.round((b.getTime() - a.getTime()) / DAY);
}

export function formatDate(iso: string | null | undefined, opts: Intl.DateTimeFormatOptions = {}): string {
  if (!iso) return "—";
  return parseDate(iso).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
    ...opts,
  });
}

/** "in 3 weeks", "today", "5 days overdue". */
export function relative(iso: string, now: Date = today()): string {
  const d = daysBetween(now, parseDate(iso));
  if (d === 0) return "today";
  const abs = Math.abs(d);
  const unit = abs >= 60 ? `${Math.round(abs / 30)} months` : abs >= 14 ? `${Math.round(abs / 7)} weeks` : `${abs} day${abs === 1 ? "" : "s"}`;
  return d > 0 ? `in ${unit}` : `${unit} ago`;
}

export function isoDate(d: Date): string {
  return d.toISOString().slice(0, 10);
}
