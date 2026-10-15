"use client";

import { AlertTriangle, CalendarClock, CheckCircle2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { daysBetween, formatDate, parseDate, relative, today } from "@/lib/dates";
import type { DeadlineOut, Roadmap } from "@/lib/types";
import { cn } from "@/lib/utils";

/** What to do now: overdue, next 30 days, next 90 days. */
export function NextActions({ deadlines, roadmap, onOpen }: { deadlines: DeadlineOut[]; roadmap: Roadmap; onOpen: (licenseId: string) => void }) {
  const now = today();
  const names = Object.fromEntries(roadmap.items.map((i) => [i.license_id, i.name]));
  const upcoming = deadlines.filter((d) => d.kind !== "obligation" || d.hard || daysBetween(now, parseDate(d.date)) < 120);
  const overdue = upcoming.filter((d) => d.overdue);
  const soon = upcoming.filter((d) => !d.overdue && daysBetween(now, parseDate(d.date)) <= 30);
  const later = upcoming.filter((d) => !d.overdue && daysBetween(now, parseDate(d.date)) > 30 && daysBetween(now, parseDate(d.date)) <= 90);
  const first = upcoming.find((d) => !d.overdue);

  if (!overdue.length && !soon.length && !later.length) {
    return (
      <div className="flex items-center gap-3 rounded-lg border bg-surface p-4 text-sm">
        <CheckCircle2 className="size-4 text-ok" />
        <span>
          Nothing due in the next 90 days.
          {first ? ` Next: ${first.title} — ${formatDate(first.date)} (${relative(first.date)}).` : ""}
        </span>
      </div>
    );
  }
  return (
    <div className="grid gap-3 md:grid-cols-3">
      <Column title="Overdue" tone="alarm" icon={<AlertTriangle />} items={overdue} names={names} onOpen={onOpen} empty="Nothing overdue." />
      <Column title="Next 30 days" tone="warn" icon={<CalendarClock />} items={soon} names={names} onOpen={onOpen} empty="Nothing due." />
      <Column title="Next 90 days" tone="neutral" icon={<CalendarClock />} items={later} names={names} onOpen={onOpen} empty="Nothing due." />
    </div>
  );
}

function Column({ title, tone, icon, items, names, onOpen, empty }: {
  title: string; tone: "alarm" | "warn" | "neutral"; icon: React.ReactNode; items: DeadlineOut[];
  names: Record<string, string>; onOpen: (id: string) => void; empty: string;
}) {
  return (
    <section className={cn("rounded-lg border bg-surface p-4", tone === "alarm" && items.length && "border-alarm/40")}>
      <h3 className={cn("flex items-center gap-2 text-sm font-semibold [&_svg]:size-4", tone === "alarm" && items.length ? "text-alarm" : tone === "warn" ? "text-warn" : "text-muted-foreground")}>
        {icon} {title} {items.length ? <span className="font-mono text-xs">({items.length})</span> : null}
      </h3>
      {items.length === 0 ? (
        <p className="mt-2 text-sm text-muted-foreground">{empty}</p>
      ) : (
        <ul className="mt-2 space-y-2">
          {items.slice(0, 5).map((d, n) => (
            <li key={`${d.license_id}-${d.kind}-${n}`}>
              <button type="button" onClick={() => onOpen(d.license_id)} className="w-full text-left text-sm hover:text-accent">
                <span className="block leading-snug">{d.title}</span>
                <span className="mt-0.5 flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground">
                  {formatDate(d.date)} · {relative(d.date)}
                  {d.hard ? <Badge tone="outline">hard</Badge> : null}
                  {d.kind === "obligation" ? <span className="truncate">· {names[d.license_id]}</span> : null}
                </span>
              </button>
            </li>
          ))}
          {items.length > 5 ? <li className="text-xs text-muted-foreground">+{items.length - 5} more in Deadlines</li> : null}
        </ul>
      )}
    </section>
  );
}
