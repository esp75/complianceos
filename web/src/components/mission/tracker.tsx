"use client";

import { Plus } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { formatDate, relative } from "@/lib/dates";
import { STATUS, countryName } from "@/lib/labels";
import type { AppStatus, Roadmap, TrackedApplication } from "@/lib/types";
import { cn } from "@/lib/utils";

const COLUMNS: { title: string; statuses: AppStatus[] }[] = [
  { title: "To do", statuses: ["not_started", "preparing"] },
  { title: "With the authority", statuses: ["submitted", "under_review", "info_requested"] },
  { title: "Decided", statuses: ["granted", "refused", "withdrawn"] },
];

export function Tracker({
  roadmap,
  applications,
  onOpen,
  onTrack,
  onTrackAll,
}: {
  roadmap: Roadmap;
  applications: TrackedApplication[];
  onOpen: (appId: string) => void;
  onTrack: (licenseId: string) => Promise<void>;
  onTrackAll: () => Promise<void>;
}) {
  const trackedIds = new Set(applications.map((a) => a.application.license_id));
  const untracked = roadmap.items.filter((i) => !trackedIds.has(i.license_id));
  const jurisdiction = (lic: string) => roadmap.items.find((i) => i.license_id === lic)?.jurisdiction ?? "";

  return (
    <div className="space-y-6">
      <div className="grid gap-4 lg:grid-cols-3">
        {COLUMNS.map((col) => {
          const cards = applications.filter((a) => col.statuses.includes(a.application.status));
          return (
            <section key={col.title} className="rounded-lg border bg-muted/40 p-3" aria-label={col.title}>
              <h3 className="mb-3 flex items-center justify-between px-1 text-sm font-semibold">
                {col.title} <span className="font-mono text-xs text-muted-foreground">{cards.length}</span>
              </h3>
              <ul className="space-y-2">
                {cards.map((t) => {
                  const s = STATUS[t.application.status];
                  const j = jurisdiction(t.application.license_id);
                  return (
                    <li key={t.application.id}>
                      <button
                        type="button"
                        onClick={() => onOpen(t.application.id)}
                        className={cn("w-full rounded-md border bg-surface p-3 text-left text-sm shadow-sm hover:border-accent/50", t.next_action.overdue && "border-alarm/50")}
                      >
                        <span className="flex items-start justify-between gap-2">
                          <span className="font-medium leading-snug">{t.item?.name ?? t.application.license_id}</span>
                          <span className="shrink-0 font-mono text-[0.7rem] uppercase text-muted-foreground">{j === "itu" ? "ITU" : j}</span>
                        </span>
                        <span className="mt-2 flex flex-wrap items-center gap-2">
                          <Badge tone={s.tone}>{s.label}</Badge>
                          {t.contacts ? <span className="text-xs text-muted-foreground">{t.contacts} contact{t.contacts === 1 ? "" : "s"}</span> : null}
                        </span>
                        <span className={cn("mt-2 block text-xs", t.next_action.overdue ? "font-medium text-alarm" : "text-muted-foreground")}>
                          {t.next_action.title}
                          {t.next_action.due ? ` · ${formatDate(t.next_action.due)} (${relative(t.next_action.due)})` : ""}
                        </span>
                      </button>
                    </li>
                  );
                })}
                {cards.length === 0 ? <li className="px-1 text-xs text-muted-foreground">Nothing here.</li> : null}
              </ul>
            </section>
          );
        })}
      </div>

      {untracked.length ? (
        <section className="rounded-lg border bg-surface p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h3 className="text-sm font-semibold">Not tracked yet ({untracked.length})</h3>
              <p className="text-xs text-muted-foreground">Track an application to record submissions, decisions and conversations.</p>
            </div>
            <Button size="sm" onClick={onTrackAll}>
              <Plus /> Track all
            </Button>
          </div>
          <ul className="mt-3 divide-y">
            {untracked.map((i) => (
              <li key={i.license_id} className="flex items-center justify-between gap-3 py-2 text-sm">
                <span>
                  {i.name} <span className="text-muted-foreground">· {i.jurisdiction === "itu" ? "ITU" : countryName(i.jurisdiction.toUpperCase())}</span>
                </span>
                <Button size="sm" variant="ghost" onClick={() => onTrack(i.license_id)}>
                  <Plus /> Track
                </Button>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  );
}
