"use client";

import { useMemo } from "react";
import { formatDate, isoDate, today } from "@/lib/dates";
import { RISK } from "@/lib/labels";
import { bar, makeScale } from "@/lib/timeline";
import type { Roadmap, RoadmapItem } from "@/lib/types";
import { cn } from "@/lib/utils";

/** Gantt-style roadmap: per licence, preparation (light) then review (solid), back from launch. */
export function Timeline({ roadmap, onOpen }: { roadmap: Roadmap; onOpen: (item: RoadmapItem) => void }) {
  const now = isoDate(today());
  const launch = roadmap.mission.target_launch_date;
  const scale = useMemo(
    () => makeScale(roadmap.items.map((i) => ({ start: i.start_by, end: i.needed_by })), [now, launch]),
    [roadmap, now, launch],
  );
  const groups = roadmap.jurisdictions.map((j) => ({ j, items: roadmap.items.filter((i) => i.jurisdiction === j.id) }));

  return (
    <div className="overflow-x-auto rounded-lg border bg-surface">
      <div className="min-w-[44rem]">
        <div className="grid grid-cols-[15rem_1fr] border-b text-xs text-muted-foreground">
          <div className="px-3 py-2">Licence</div>
          <div className="relative h-8">
            {scale.months.map((m) => (
              <span key={m.iso} className={cn("absolute top-2 -translate-x-1/2 whitespace-nowrap", m.year && "font-semibold text-foreground")} style={{ left: `${m.x}%` }}>
                {m.label}
              </span>
            ))}
          </div>
        </div>
        {groups.map(({ j, items }) => (
          <div key={j.id}>
            <div className="border-b bg-muted/60 px-3 py-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">{j.name}</div>
            {items.map((i) => {
              const prep = bar(scale, i.start_by, i.submit_by);
              const review = bar(scale, i.submit_by, i.needed_by);
              const late = i.risk === "late";
              return (
                <button
                  key={i.license_id}
                  type="button"
                  onClick={() => onOpen(i)}
                  className="group grid w-full grid-cols-[15rem_1fr] border-b text-left last:border-b-0 hover:bg-muted/50"
                  aria-label={`${i.name}: start by ${formatDate(i.start_by)}, submit by ${formatDate(i.submit_by)}, ${RISK[i.risk].label}`}
                >
                  <span className="flex items-center gap-2 truncate px-3 py-2.5 text-sm">
                    {i.critical ? <span className="size-1.5 shrink-0 rounded-full bg-accent" title="Critical path" /> : <span className="size-1.5 shrink-0" />}
                    <span className="truncate group-hover:text-accent">{i.name}</span>
                  </span>
                  <span className="relative my-2 mr-3">
                    <Gridlines months={scale.months.map((m) => m.x)} />
                    <span
                      className={cn("absolute top-1/2 h-3 -translate-y-1/2 rounded-l-sm", late ? "bg-alarm/25" : i.critical ? "bg-accent/25" : "bg-muted-foreground/20")}
                      style={{ left: `${prep.left}%`, width: `${prep.width}%` }}
                    />
                    <span
                      className={cn("absolute top-1/2 h-3 -translate-y-1/2 rounded-r-sm", late ? "bg-alarm" : i.critical ? "bg-accent" : "bg-muted-foreground/60")}
                      style={{ left: `${review.left}%`, width: `${review.width}%` }}
                    />
                  </span>
                </button>
              );
            })}
          </div>
        ))}
        <div className="relative grid grid-cols-[15rem_1fr] text-[0.7rem]">
          <div className="px-3 py-2 text-muted-foreground">
            <Legend />
          </div>
          <div className="relative h-8">
            <Marker x={scale.x(now)} label="Today" className="text-muted-foreground" />
            <Marker x={scale.x(launch)} label={`Launch ${formatDate(launch)}`} className="text-accent" />
          </div>
        </div>
      </div>
    </div>
  );
}

function Gridlines({ months }: { months: number[] }) {
  return (
    <span className="pointer-events-none absolute inset-0" aria-hidden="true">
      {months.map((x) => (
        <span key={x} className="absolute inset-y-0 border-l border-dashed border-border" style={{ left: `${x}%` }} />
      ))}
    </span>
  );
}

function Marker({ x, label, className }: { x: number; label: string; className?: string }) {
  return (
    <span
      className={cn(
        "absolute top-1 whitespace-nowrap font-medium",
        x > 85 ? "-translate-x-full" : x < 15 ? "" : "-translate-x-1/2",
        className,
      )}
      style={{ left: `${x}%` }}
    >
      {x > 85 ? `${label} ▲` : `▲ ${label}`}
    </span>
  );
}

function Legend() {
  return (
    <span className="flex flex-wrap items-center gap-3">
      <span className="inline-flex items-center gap-1">
        <span className="h-2 w-4 rounded-l-sm bg-muted-foreground/20" /> prepare
      </span>
      <span className="inline-flex items-center gap-1">
        <span className="h-2 w-4 rounded-r-sm bg-muted-foreground/60" /> review
      </span>
      <span className="inline-flex items-center gap-1">
        <span className="size-1.5 rounded-full bg-accent" /> critical
      </span>
    </span>
  );
}
