"use client";

import { AlertTriangle, CalendarPlus, ChevronRight, FileDown, Pencil, Trash2 } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { ApiNotice } from "@/components/api-notice";
import { ApplicationSheet } from "@/components/mission/application-sheet";
import { BriefView } from "@/components/mission/brief";
import { Deadlines } from "@/components/mission/deadlines";
import { LicenseSheet } from "@/components/mission/license-sheet";
import { NextActions } from "@/components/mission/next-actions";
import { Timeline } from "@/components/mission/timeline";
import { Tracker } from "@/components/mission/tracker";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { api, paths, useApi } from "@/lib/api";
import { formatDate, relative } from "@/lib/dates";
import { BASIS, CATEGORY, ORBITS, RISK, STATUS, countryName } from "@/lib/labels";
import type { DeadlineOut, Mission, Roadmap, RoadmapItem, TrackedApplication } from "@/lib/types";

export default function MissionPage({ params }: { params: { id: string } }) {
  const id = params.id;
  const router = useRouter();
  const mission = useApi<Mission>(paths.mission(id));
  const roadmap = useApi<Roadmap>(paths.roadmap(id));
  const apps = useApi<TrackedApplication[]>(paths.applications(id));
  const deadlines = useApi<DeadlineOut[]>(paths.deadlines(id));
  const [licenseId, setLicenseId] = useState<string | null>(null);
  const [appId, setAppId] = useState<string | null>(null);
  const [tab, setTab] = useState("roadmap");
  const [confirmDelete, setConfirmDelete] = useState(false);

  const refresh = async () => {
    await Promise.all([apps.mutate(), deadlines.mutate()]);
  };
  const track = async (lic: string) => {
    await api.track(id, lic);
    await refresh();
  };

  if (mission.error || roadmap.error) {
    return (
      <div className="container py-10">
        <ApiNotice error={mission.error ?? roadmap.error} />
      </div>
    );
  }
  if (!mission.data || !roadmap.data) return <div className="container py-10 text-muted-foreground">Loading…</div>;

  const r = roadmap.data;
  const m = mission.data.profile;
  const tracked = apps.data ?? [];
  const byLicense = Object.fromEntries(tracked.map((t) => [t.application.license_id, t]));
  const item: RoadmapItem | null = licenseId ? r.items.find((i) => i.license_id === licenseId) ?? null : null;
  const openApp = tracked.find((t) => t.application.id === appId) ?? null;
  const late = r.items.filter((i) => i.risk === "late").length;
  const overdue = (deadlines.data ?? []).filter((d) => d.overdue).length;
  const first = r.items[0];

  return (
    <div className="container py-8">
      <nav className="mb-3 text-sm text-muted-foreground" aria-label="Breadcrumb">
        <Link href="/" className="hover:text-foreground">Missions</Link> <ChevronRight className="inline size-3" /> {m.name}
      </nav>

      <header className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{m.name}</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {m.operator_name ? `${m.operator_name} · ` : ""}
            {countryName(m.operator_country)} · {m.satellite_count} satellite{m.satellite_count === 1 ? "" : "s"} · {ORBITS[m.orbit]}
            {m.altitude_km ? ` at ${m.altitude_km} km` : ""} · launch {formatDate(m.target_launch_date)} ({relative(m.target_launch_date)})
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button asChild size="sm">
            <Link href={`/missions/${id}/edit`}>
              <Pencil /> Edit mission
            </Link>
          </Button>
          <Button asChild size="sm">
            <a href={paths.calendar(id)}>
              <CalendarPlus /> Calendar
            </a>
          </Button>
          <Button asChild size="sm" variant="primary">
            <a href={paths.dossier(id)}>
              <FileDown /> Download dossier (PDF)
            </a>
          </Button>
          {confirmDelete ? (
            <Button
              size="sm"
              variant="danger"
              onClick={async () => {
                await api.deleteMission(id);
                router.push("/");
              }}
            >
              Confirm delete
            </Button>
          ) : (
            <Button size="sm" variant="ghost" onClick={() => setConfirmDelete(true)} aria-label="Delete mission">
              <Trash2 />
            </Button>
          )}
        </div>
      </header>

      <dl className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Summary label="Licences & filings" value={String(r.items.length)} sub={`${r.jurisdictions.length} jurisdictions`} />
        <Summary label="Start first" value={first ? formatDate(first.start_by) : "—"} sub={first ? first.name : ""} />
        <Summary label="At risk" value={String(late)} sub={late ? "cannot meet the launch date" : "none late at typical times"} tone={late ? "alarm" : "ok"} />
        <Summary label="Tracked" value={`${tracked.length}/${r.items.length}`} sub={overdue ? `${overdue} overdue date${overdue === 1 ? "" : "s"}` : "nothing overdue"} tone={overdue ? "alarm" : undefined} />
      </dl>

      {r.warnings.length ? (
        <div className="mt-4 space-y-1.5 rounded-lg border border-warn/40 bg-warn-soft p-4 text-sm" role="status">
          {r.warnings.map((w) => (
            <p key={w} className="flex gap-2">
              <AlertTriangle className="mt-0.5 size-4 shrink-0 text-warn" /> {w}
            </p>
          ))}
        </div>
      ) : null}

      <Tabs value={tab} onValueChange={setTab} className="mt-8">
        <TabsList>
          <TabsTrigger value="roadmap">Roadmap</TabsTrigger>
          <TabsTrigger value="tracker">
            Tracker <Badge tone="neutral">{tracked.length}</Badge>
          </TabsTrigger>
          <TabsTrigger value="deadlines">
            Deadlines {overdue ? <Badge tone="alarm">{overdue}</Badge> : null}
          </TabsTrigger>
          <TabsTrigger value="brief">Brief</TabsTrigger>
        </TabsList>

        <TabsContent value="roadmap" className="mt-6 space-y-8">
          {deadlines.data ? <NextActions deadlines={deadlines.data} roadmap={r} onOpen={setLicenseId} /> : null}
          <Timeline roadmap={r} onOpen={(i) => setLicenseId(i.license_id)} />
          <div className="space-y-6">
            {r.jurisdictions.map((j) => (
              <section key={j.id}>
                <h2 className="mb-2 flex items-baseline gap-2 text-base font-semibold">
                  {j.name}
                  <span className="text-sm font-normal text-muted-foreground">
                    {j.licence_count} item{j.licence_count === 1 ? "" : "s"} · start from {formatDate(j.earliest_start_by)}
                  </span>
                </h2>
                <ul className="divide-y rounded-lg border bg-surface">
                  {r.items
                    .filter((i) => i.jurisdiction === j.id)
                    .map((i) => {
                      const t = byLicense[i.license_id];
                      return (
                        <li key={i.license_id}>
                          <button type="button" onClick={() => setLicenseId(i.license_id)} className="flex w-full flex-col gap-1.5 px-4 py-3 text-left hover:bg-muted/50 sm:flex-row sm:items-center sm:gap-4">
                            <span className="min-w-0 flex-1">
                              <span className="flex flex-wrap items-center gap-2 font-medium">
                                {i.critical ? <span className="size-1.5 rounded-full bg-accent" title="Critical path" /> : null}
                                {i.name}
                              </span>
                              <span className="mt-0.5 block truncate text-xs text-muted-foreground">
                                {r.authorities[i.authority_id]?.authority.name} · {CATEGORY[i.category] ?? i.category}
                              </span>
                            </span>
                            <span className="flex shrink-0 flex-wrap items-center gap-2 text-xs">
                              <span className="tabular-nums text-muted-foreground">start by {formatDate(i.start_by)}</span>
                              <Badge tone={BASIS[i.review.basis].tone} title={BASIS[i.review.basis].hint}>
                                {BASIS[i.review.basis].label}
                              </Badge>
                              <Badge tone={RISK[i.risk].tone}>{RISK[i.risk].label}</Badge>
                              {t ? <Badge tone={STATUS[t.application.status].tone}>{STATUS[t.application.status].label}</Badge> : null}
                            </span>
                          </button>
                        </li>
                      );
                    })}
                </ul>
              </section>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="tracker" className="mt-6">
          <Tracker
            roadmap={r}
            applications={tracked}
            onOpen={setAppId}
            onTrack={track}
            onTrackAll={async () => {
              for (const i of r.items) if (!byLicense[i.license_id]) await api.track(id, i.license_id);
              await refresh();
            }}
          />
        </TabsContent>

        <TabsContent value="deadlines" className="mt-6">
          {deadlines.data ? <Deadlines missionId={id} roadmap={r} deadlines={deadlines.data} onOpen={setLicenseId} /> : null}
        </TabsContent>

        <TabsContent value="brief" className="mt-6">
          <BriefView missionId={id} version={mission.data.updated_at} />
        </TabsContent>
      </Tabs>

      <LicenseSheet
        roadmap={r}
        item={item}
        missionId={id}
        tracked={item ? byLicense[item.license_id] : undefined}
        onClose={() => setLicenseId(null)}
        onTrack={track}
        onOpenApplication={(a) => {
          setLicenseId(null);
          setAppId(a);
        }}
      />
      <ApplicationSheet
        tracked={openApp}
        onClose={() => setAppId(null)}
        onChanged={refresh}
        onOpenLicense={(lic) => {
          setAppId(null);
          setLicenseId(lic);
        }}
      />
    </div>
  );
}

function Summary({ label, value, sub, tone }: { label: string; value: string; sub: string; tone?: "alarm" | "ok" }) {
  return (
    <div className="rounded-lg border bg-surface p-4">
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className={`mt-1 text-xl font-semibold tabular-nums ${tone === "alarm" ? "text-alarm" : tone === "ok" ? "text-ok" : ""}`}>{value}</dd>
      <dd className="mt-0.5 truncate text-xs text-muted-foreground">{sub}</dd>
    </div>
  );
}
