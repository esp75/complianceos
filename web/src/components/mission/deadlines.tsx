"use client";

import { CalendarPlus } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { paths } from "@/lib/api";
import { formatDate, parseDate, relative } from "@/lib/dates";
import type { DeadlineOut, Roadmap } from "@/lib/types";
import { cn } from "@/lib/utils";

const KIND = { start: "Start", submit: "Submit", obligation: "Obligation" } as const;

export function Deadlines({ missionId, roadmap, deadlines, onOpen }: {
  missionId: string; roadmap: Roadmap; deadlines: DeadlineOut[]; onOpen: (licenseId: string) => void;
}) {
  const names = Object.fromEntries(roadmap.items.map((i) => [i.license_id, i.name]));
  const months = new Map<string, DeadlineOut[]>();
  for (const d of deadlines) {
    const key = d.date.slice(0, 7);
    months.set(key, [...(months.get(key) ?? []), d]);
  }
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-muted-foreground">
          Every start, submission and obligation date. Dates tied to a submission or grant move once you record the real date in the tracker.
        </p>
        <Button asChild size="sm">
          <a href={paths.calendar(missionId)}>
            <CalendarPlus /> Add to calendar (.ics)
          </a>
        </Button>
      </div>
      <div className="rounded-lg border bg-surface">
        {[...months.entries()].map(([month, items]) => (
          <section key={month} className="border-b last:border-b-0">
            <h3 className="sticky top-14 z-10 bg-surface/95 px-4 py-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground backdrop-blur">
              {parseDate(`${month}-01`).toLocaleDateString("en-GB", { month: "long", year: "numeric", timeZone: "UTC" })}
            </h3>
            <ul>
              {items.map((d, n) => (
                <li key={`${d.license_id}-${d.kind}-${n}`}>
                  <button
                    type="button"
                    onClick={() => onOpen(d.license_id)}
                    className="grid w-full grid-cols-[6.5rem_1fr] gap-3 px-4 py-2.5 text-left text-sm hover:bg-muted/50 sm:grid-cols-[7rem_6rem_1fr]"
                  >
                    <span className={cn("tabular-nums", d.overdue && "font-medium text-alarm")}>
                      {formatDate(d.date)}
                      <span className="block text-xs text-muted-foreground">{relative(d.date)}</span>
                    </span>
                    <span className="hidden sm:block">
                      <Badge tone={d.kind === "submit" ? "accent" : d.kind === "start" ? "neutral" : "outline"}>{KIND[d.kind]}</Badge>
                    </span>
                    <span>
                      <span className="flex flex-wrap items-center gap-2">
                        {d.title}
                        {d.hard ? <Badge tone="outline">hard</Badge> : null}
                        {d.overdue ? <Badge tone="alarm">overdue</Badge> : null}
                      </span>
                      {d.kind === "obligation" ? <span className="block text-xs text-muted-foreground">{names[d.license_id]}</span> : null}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>
    </div>
  );
}
