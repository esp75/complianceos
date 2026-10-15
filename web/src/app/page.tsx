"use client";

import { ArrowRight, CalendarClock, FileSearch, ListChecks, Satellite } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { ApiNotice } from "@/components/api-notice";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { api, paths, useApi } from "@/lib/api";
import { formatDate, relative } from "@/lib/dates";
import { countryName } from "@/lib/labels";
import type { JurisdictionOut, Mission } from "@/lib/types";

export default function Home() {
  const router = useRouter();
  const missions = useApi<Mission[]>(paths.missions);
  const coverage = useApi<JurisdictionOut[]>(paths.jurisdictions);
  const [opening, setOpening] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function openSample() {
    setOpening(true);
    setError(null);
    try {
      const m = await api.createSample();
      router.push(`/missions/${m.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setOpening(false);
    }
  }

  return (
    <div className="container py-10 sm:py-14">
      <section className="max-w-3xl">
        <Badge tone="accent" className="mb-4">
          Open source · open data
        </Badge>
        <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">Plan your satellite licensing path</h1>
        <p className="mt-4 text-lg leading-relaxed text-muted-foreground">
          Describe your mission once. See every licence, authorisation and ITU filing it needs in each country, why
          each one applies, quoted from the law, and the dates to start each one, worked back from your launch.
          Then track your applications so nothing slips.
        </p>
        <div className="mt-7 flex flex-wrap gap-3">
          <Button asChild variant="primary" size="lg">
            <Link href="/missions/new">
              Plan a mission <ArrowRight />
            </Link>
          </Button>
          <Button size="lg" onClick={openSample} disabled={opening}>
            <Satellite /> {opening ? "Opening…" : "Open the sample mission"}
          </Button>
        </div>
        {error ? <p className="mt-3 text-sm text-alarm">{error}</p> : null}
      </section>

      <ApiNotice error={missions.error} />

      <section className="mt-12 grid gap-4 sm:grid-cols-3" aria-label="How it works">
        <Step icon={<ListChecks />} title="1 · Describe the mission">
          Where you are established, where you operate from, which markets you serve, which radio services and
          bands you use, and when you want to launch.
        </Step>
        <Step icon={<FileSearch />} title="2 · Get a cited roadmap">
          Each requirement shows the rule that triggered it and the article of law behind it, with the official
          text one click away.
        </Step>
        <Step icon={<CalendarClock />} title="3 · Track to approval">
          Log submissions, grants and conversations with authorities. Deadlines and renewals follow, and export to
          your calendar.
        </Step>
      </section>

      {missions.data && missions.data.length > 0 ? (
        <section className="mt-12">
          <h2 className="text-lg font-semibold">Your missions</h2>
          <ul className="mt-4 grid gap-3 sm:grid-cols-2">
            {missions.data.map((m) => (
              <li key={m.id}>
                <Link href={`/missions/${m.id}`} className="block rounded-lg border bg-surface p-4 transition-colors hover:border-accent/50">
                  <p className="font-medium">{m.profile.name}</p>
                  <p className="mt-1 text-sm text-muted-foreground">
                    Launch {formatDate(m.profile.target_launch_date)} ({relative(m.profile.target_launch_date)}) ·{" "}
                    {m.profile.satellite_count} satellite{m.profile.satellite_count === 1 ? "" : "s"} · {m.profile.orbit}
                  </p>
                  <p className="mt-2 text-xs text-muted-foreground">
                    Operator: {countryName(m.profile.operator_country)}
                    {m.profile.service_countries?.length ? ` · Markets: ${m.profile.service_countries.join(", ")}` : ""}
                  </p>
                </Link>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {coverage.data ? (
        <section className="mt-12">
          <h2 className="text-lg font-semibold">What the data covers today</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Researched from official sources and open for review. Countries outside this list are flagged in your
            roadmap rather than left out silently.
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            {coverage.data.map((j) => (
              <Badge key={j.jurisdiction.id} tone="outline" className="px-2 py-1 text-sm">
                {j.jurisdiction.name}
                <span className="text-muted-foreground">· {j.licenses.length}</span>
              </Badge>
            ))}
            <Link href="/data" className="self-center text-sm text-accent hover:underline">
              Sources and how to contribute →
            </Link>
          </div>
        </section>
      ) : null}
    </div>
  );
}

function Step({ icon, title, children }: { icon: React.ReactNode; title: string; children: React.ReactNode }) {
  return (
    <Card className="p-5">
      <div className="mb-3 inline-flex size-9 items-center justify-center rounded-md bg-accent-soft text-accent [&_svg]:size-5">{icon}</div>
      <h3 className="font-semibold">{title}</h3>
      <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{children}</p>
    </Card>
  );
}
