"use client";

import { Building2, ExternalLink, Globe, Mail, MapPin, Phone, Send } from "lucide-react";
import { useState } from "react";
import { ApiNotice } from "@/components/api-notice";
import { Badge } from "@/components/ui/badge";
import { paths, useApi } from "@/lib/api";
import { formatDate } from "@/lib/dates";
import { CATEGORY } from "@/lib/labels";
import { correctionUrl } from "@/lib/site";
import type { Facilitator, JurisdictionOut } from "@/lib/types";
import { contactHref, safeHref } from "@/lib/links";
import { cn } from "@/lib/utils";

const ICON = { email: Mail, phone: Phone, postal: MapPin, web: Globe, web_form: Send, portal: Globe };

export default function Directory() {
  const js = useApi<JurisdictionOut[]>(paths.jurisdictions);
  const fs = useApi<Facilitator[]>(paths.facilitators);
  const [filter, setFilter] = useState<string>("all");
  const shown = (js.data ?? []).filter((j) => filter === "all" || j.jurisdiction.id === filter);

  return (
    <div className="container py-8">
      <h1 className="text-2xl font-semibold tracking-tight">Directory</h1>
      <p className="mt-1 max-w-2xl text-muted-foreground">
        The authorities that decide, with the contact channels they publish themselves, and firms that help operators
        through licensing. Institutional contacts only; firms are listed in their own words, without ranking.
      </p>
      <ApiNotice error={js.error} />

      <div className="mt-6 flex flex-wrap gap-2" role="group" aria-label="Filter by jurisdiction">
        {[{ id: "all", name: "All" }, ...(js.data ?? []).map((j) => ({ id: j.jurisdiction.id, name: j.jurisdiction.name }))].map((o) => (
          <button
            key={o.id}
            type="button"
            aria-pressed={filter === o.id}
            onClick={() => setFilter(o.id)}
            className={cn("rounded-full border px-3 py-1 text-sm", filter === o.id ? "border-accent bg-accent-soft text-accent" : "hover:bg-muted")}
          >
            {o.name}
          </button>
        ))}
      </div>

      <div className="mt-8 space-y-10">
        {shown.map(({ jurisdiction: j }) => {
          const firms = (fs.data ?? []).filter((f) => f.jurisdictions.includes(j.id));
          return (
            <section key={j.id}>
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <h2 className="text-lg font-semibold">{j.name}</h2>
                <p className="text-xs text-muted-foreground">
                  Last verified {formatDate(j.last_verified)} · {j.status === "draft" ? "draft data" : "reviewed"} ·{" "}
                  <a href={correctionUrl(j.name)} className="underline underline-offset-2 hover:text-foreground">suggest a correction</a>
                </p>
              </div>
              <p className="mt-1 max-w-3xl text-sm text-muted-foreground">{j.summary}</p>
              <div className="mt-4 grid gap-3 md:grid-cols-2">
                {j.authorities.map((a) => (
                  <article key={a.id} className="rounded-lg border bg-surface p-4 text-sm">
                    <div className="flex gap-2">
                      <Building2 className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
                      <div>
                        <a href={safeHref(a.website)} target="_blank" rel="noreferrer" className="font-medium hover:text-accent">
                          {a.name} <ExternalLink className="inline size-3" />
                        </a>
                        {a.name_en ? <p className="text-xs text-muted-foreground">{a.name_en}</p> : null}
                        <div className="mt-2 flex flex-wrap gap-1">
                          {a.roles.map((r) => (
                            <Badge key={r} tone="neutral">{r.replaceAll("_", " ")}</Badge>
                          ))}
                        </div>
                      </div>
                    </div>
                    {a.contacts?.length ? (
                      <ul className="mt-3 space-y-2 border-t pt-3">
                        {a.contacts.map((c) => {
                          const Icon = ICON[c.kind] ?? Globe;
                          const href = contactHref(c.kind, c.value);
                          return (
                            <li key={c.value} className="flex gap-2">
                              <Icon className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
                              <div>
                                {href ? <a href={href} className="break-all text-accent hover:underline">{c.value}</a> : c.value}
                                <p className="text-xs text-muted-foreground">
                                  {c.purpose} Source: <a href={safeHref(c.source.url)} target="_blank" rel="noreferrer" className="underline underline-offset-2">{c.source.title}</a>, {formatDate(c.source.retrieved)}.
                                </p>
                              </div>
                            </li>
                          );
                        })}
                      </ul>
                    ) : (
                      <p className="mt-3 border-t pt-3 text-xs text-muted-foreground">{a.notes ?? "No verified contact channels yet."}</p>
                    )}
                  </article>
                ))}
              </div>
              <h3 className="mt-5 text-sm font-semibold">Firms</h3>
              {firms.length ? (
                <ul className="mt-2 grid gap-3 md:grid-cols-2">
                  {firms.map((f) => (
                    <li key={f.id} className="rounded-lg border bg-surface p-4 text-sm">
                      <a href={safeHref(f.website)} target="_blank" rel="noreferrer" className="font-medium hover:text-accent">
                        {f.name} <ExternalLink className="inline size-3" />
                      </a>
                      <p className="mt-1 text-muted-foreground">{f.description}</p>
                      <div className="mt-2 flex flex-wrap gap-1">
                        <Badge tone="outline">{f.kind.replace("_", " ")}</Badge>
                        {f.services.map((s) => (
                          <Badge key={s} tone="neutral">{CATEGORY[s] ?? s}</Badge>
                        ))}
                      </div>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="mt-2 text-sm text-muted-foreground">No firms listed yet. Firms can be added by pull request (see Data &amp; sources).</p>
              )}
            </section>
          );
        })}
      </div>
    </div>
  );
}
