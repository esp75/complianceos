"use client";

import { Building2, Copy, ExternalLink, Mail, MapPin, Phone, Globe, Send } from "lucide-react";
import { useState } from "react";
import { Cite, CitationBody } from "@/components/cite";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent } from "@/components/ui/sheet";
import { api } from "@/lib/api";
import { formatDate, relative } from "@/lib/dates";
import { BASIS, CATEGORY, RISK, STATUS } from "@/lib/labels";
import { correctionUrl } from "@/lib/site";
import { contactHref, safeHref } from "@/lib/links";
import type { Authority, EmailDraft, Roadmap, RoadmapItem, TrackedApplication } from "@/lib/types";

export function LicenseSheet({
  roadmap,
  item,
  missionId,
  tracked,
  onClose,
  onTrack,
  onOpenApplication,
}: {
  roadmap: Roadmap;
  item: RoadmapItem | null;
  missionId: string;
  tracked: TrackedApplication | undefined;
  onClose: () => void;
  onTrack: (licenseId: string) => Promise<void>;
  onOpenApplication: (appId: string) => void;
}) {
  return (
    <Sheet open={item !== null} onOpenChange={(o) => !o && onClose()}>
      {item ? (
        <SheetContent
          title={item.name}
          description={
            <span className="flex flex-wrap items-center gap-2">
              {item.name_local ? <span className="italic">{item.name_local}</span> : null}
              <Badge tone="neutral">{CATEGORY[item.category] ?? item.category}</Badge>
              <Badge tone={RISK[item.risk].tone}>{RISK[item.risk].label}</Badge>
              {item.critical ? <Badge tone="accent">Critical path</Badge> : null}
              {item.status === "draft" ? <Badge tone="dashed">Draft data</Badge> : <Badge tone="ok">Reviewed</Badge>}
            </span>
          }
        >
          <Body roadmap={roadmap} item={item} missionId={missionId} tracked={tracked} onTrack={onTrack} onOpenApplication={onOpenApplication} />
        </SheetContent>
      ) : null}
    </Sheet>
  );
}

function Body({ roadmap, item, missionId, tracked, onTrack, onOpenApplication }: {
  roadmap: Roadmap; item: RoadmapItem; missionId: string; tracked: TrackedApplication | undefined;
  onTrack: (id: string) => Promise<void>; onOpenApplication: (id: string) => void;
}) {
  const [busy, setBusy] = useState(false);
  const authority = roadmap.authorities[item.authority_id]?.authority;
  const prereqs = item.prerequisites.map((p) => ({ ...p, name: roadmap.items.find((i) => i.license_id === p.license_id)?.name ?? p.license_id }));
  return (
    <div className="space-y-7 text-sm">
      <p className="leading-relaxed">{item.summary}</p>

      <div className="flex flex-wrap items-center gap-3 rounded-md border bg-surface p-3">
        {tracked ? (
          <>
            <Badge tone={STATUS[tracked.application.status].tone}>{STATUS[tracked.application.status].label}</Badge>
            <span className="text-muted-foreground">{tracked.next_action.title}</span>
            <Button size="sm" className="ml-auto" onClick={() => onOpenApplication(tracked.application.id)}>
              Open application
            </Button>
          </>
        ) : (
          <>
            <span className="text-muted-foreground">Not tracked yet.</span>
            <Button
              size="sm"
              variant="primary"
              className="ml-auto"
              disabled={busy}
              onClick={async () => {
                setBusy(true);
                await onTrack(item.license_id).finally(() => setBusy(false));
              }}
            >
              Track this application
            </Button>
          </>
        )}
      </div>

      <Section title="Why this applies to you">
        <ul className="space-y-2">
          {item.reasons.map((r) => (
            <li key={r.text} className="flex gap-2">
              <span className="mt-2 size-1.5 shrink-0 rounded-full bg-accent" />
              <span className="leading-relaxed">
                {r.text}
                {r.cite.map((c) => (
                  <Cite key={c} id={c} citations={roadmap.citations} />
                ))}
              </span>
            </li>
          ))}
        </ul>
      </Section>

      <Section title="Timing">
        <dl className="grid grid-cols-2 gap-x-4 gap-y-3 sm:grid-cols-4">
          <Stat label="Start by" value={formatDate(item.start_by)} sub={relative(item.start_by)} />
          <Stat label="Submit by" value={formatDate(item.submit_by)} sub={relative(item.submit_by)} />
          <Stat label="Needed by" value={formatDate(item.needed_by)} sub={item.needed_for === "launch" ? "launch" : "service start"} />
          <Stat label="Slack" value={`${Math.round(item.slack_days / 7)} wk`} sub={RISK[item.risk].label.toLowerCase()} />
        </dl>
        <div className="mt-4 space-y-2">
          <DurationRow label="Preparation" d={item.preparation} citations={roadmap.citations} />
          <DurationRow label="Authority review" d={item.review} citations={roadmap.citations} />
        </div>
        {prereqs.length ? (
          <p className="mt-3 text-muted-foreground">
            Waits for:{" "}
            {prereqs.map((p, n) => (
              <span key={p.license_id}>
                {n ? "; " : ""}
                <span className="text-foreground">{p.name}</span> ({p.stage})
              </span>
            ))}
          </p>
        ) : null}
      </Section>

      <Section title="Legal basis">
        <div className="space-y-4">
          {item.legal_basis.map((id) => {
            const c = roadmap.citations[id];
            return c ? (
              <div key={id} className="rounded-md border bg-surface p-3">
                <CitationBody c={c} />
              </div>
            ) : null;
          })}
        </div>
      </Section>

      {item.documents.length || item.fees ? (
        <Section title="What you'll need">
          {item.documents.length ? (
            <ul className="list-inside list-disc space-y-1 marker:text-muted-foreground">
              {item.documents.map((d) => (
                <li key={d}>{d}</li>
              ))}
            </ul>
          ) : null}
          {item.fees ? <p className="mt-3"><span className="font-medium">Fees: </span>{item.fees}</p> : null}
        </Section>
      ) : null}

      {item.requires_local_presence !== false ? (
        <Section title="Local presence">
          <p>
            {item.requires_local_presence === true ? (
              <Badge tone="warn" className="mr-2">Required</Badge>
            ) : (
              <Badge tone="dashed" className="mr-2">Not established</Badge>
            )}
            {item.local_presence_note ?? "Ask the authority whether a local entity or representative is needed."}
          </p>
        </Section>
      ) : null}

      {item.obligations.length ? (
        <Section title="Obligations that follow">
          <ul className="space-y-2">
            {item.obligations.filter((o) => o.occurrence === 1).map((o) => (
              <li key={o.id} className="flex flex-wrap items-baseline gap-x-2">
                {o.kind === "hard" ? <Badge tone="outline">hard</Badge> : <Badge tone="neutral">soft</Badge>}
                <span className="font-medium">{o.name}</span>
                <span className="text-muted-foreground">
                  — {o.when}
                  {o.recurring ? "" : ` (${formatDate(o.due)} if you start now)`}
                </span>
                {o.cite.map((c) => (
                  <Cite key={c} id={c} citations={roadmap.citations} />
                ))}
              </li>
            ))}
          </ul>
        </Section>
      ) : null}

      {authority ? <AuthorityCard authority={authority} missionId={missionId} item={item} /> : null}

      <Section title="Outside help">
        {item.facilitators.length ? (
          <ul className="space-y-3">
            {item.facilitators.map((f) => {
              const fac = roadmap.facilitators[f];
              return fac ? (
                <li key={f} className="rounded-md border bg-surface p-3">
                  <div className="flex items-center justify-between gap-2">
                    <a href={safeHref(fac.website)} target="_blank" rel="noreferrer" className="font-medium hover:text-accent">
                      {fac.name} <ExternalLink className="inline size-3" />
                    </a>
                    <EmailButton missionId={missionId} licenseId={item.license_id} recipient={f} label="Draft enquiry" />
                  </div>
                  <p className="mt-1 text-muted-foreground">{fac.description}</p>
                </li>
              ) : null;
            })}
          </ul>
        ) : (
          <p className="text-muted-foreground">No firms listed for this yet. The directory is open to contributions.</p>
        )}
        <p className="mt-3 text-xs text-muted-foreground">Listed neutrally, in their own words. No ranking, no paid placement.</p>
      </Section>

      <p className="border-t pt-4 text-xs text-muted-foreground">
        Last verified {formatDate(item.last_verified)}.{" "}
        <a href={correctionUrl(item.name)} className="underline underline-offset-2 hover:text-foreground">
          Suggest a correction
        </a>
      </p>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section>
      <h3 className="mb-2.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">{title}</h3>
      {children}
    </section>
  );
}

function Stat({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div>
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="font-medium tabular-nums">{value}</dd>
      {sub ? <dd className="text-xs text-muted-foreground">{sub}</dd> : null}
    </div>
  );
}

function DurationRow({ label, d, citations }: { label: string; d: RoadmapItem["review"]; citations: Roadmap["citations"] }) {
  const b = BASIS[d.basis];
  return (
    <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
      <span className="w-36 shrink-0 text-muted-foreground">{label}</span>
      <span className="font-medium tabular-nums">
        {d.typical_weeks} weeks <span className="font-normal text-muted-foreground">(range {d.min_weeks}–{d.max_weeks})</span>
      </span>
      <Badge tone={b.tone} title={b.hint}>{b.label}</Badge>
      {(d.cite ?? []).map((c) => (
        <Cite key={c} id={c} citations={citations} />
      ))}
      {d.note ? <p className="basis-full text-xs text-muted-foreground sm:pl-[9.5rem]">{d.note}</p> : null}
    </div>
  );
}

const CHANNEL_ICON = { email: Mail, phone: Phone, postal: MapPin, web: Globe, web_form: Send, portal: Globe };

function AuthorityCard({ authority, missionId, item }: { authority: Authority; missionId: string; item: RoadmapItem }) {
  return (
    <Section title="Who to contact">
      <div className="rounded-md border bg-surface p-3">
        <div className="flex items-start justify-between gap-3">
          <div className="flex gap-2">
            <Building2 className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
            <div>
              <a href={safeHref(authority.website)} target="_blank" rel="noreferrer" className="font-medium hover:text-accent">
                {authority.name}
              </a>
              {authority.name_en ? <p className="text-xs text-muted-foreground">{authority.name_en}</p> : null}
            </div>
          </div>
          <EmailButton missionId={missionId} licenseId={item.license_id} recipient={authority.id} label="Draft first email" />
        </div>
        {authority.contacts?.length ? (
          <ul className="mt-3 space-y-2">
            {authority.contacts.map((c) => {
              const Icon = CHANNEL_ICON[c.kind] ?? Globe;
              const href = contactHref(c.kind, c.value);
              return (
                <li key={`${c.kind}-${c.value}`} className="flex gap-2">
                  <Icon className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
                  <div>
                    {href ? (
                      <a href={href} target={href.startsWith("http") ? "_blank" : undefined} rel="noreferrer" className="break-all text-accent hover:underline">
                        {c.value}
                      </a>
                    ) : (
                      <span>{c.value}</span>
                    )}
                    <p className="text-xs text-muted-foreground">{c.purpose}</p>
                  </div>
                </li>
              );
            })}
          </ul>
        ) : (
          <p className="mt-2 text-muted-foreground">Contact channels not yet verified; start from the authority&apos;s website.</p>
        )}
        {authority.notes ? <p className="mt-3 text-xs text-muted-foreground">{authority.notes}</p> : null}
      </div>
    </Section>
  );
}

function EmailButton({ missionId, licenseId, recipient, label }: { missionId: string; licenseId: string; recipient: string; label: string }) {
  const [draft, setDraft] = useState<EmailDraft | null>(null);
  const [copied, setCopied] = useState(false);
  return (
    <div className="shrink-0 text-right">
      {!draft ? (
        <Button size="sm" variant="ghost" onClick={async () => setDraft(await api.introEmail(missionId, licenseId, recipient))}>
          <Mail /> {label}
        </Button>
      ) : (
        <div className="fixed inset-x-4 bottom-4 z-[60] mx-auto max-w-xl rounded-lg border bg-surface p-4 text-left shadow-xl sm:absolute sm:inset-x-auto sm:bottom-auto sm:right-6 sm:mt-2 sm:w-[30rem]">
          <p className="text-xs text-muted-foreground">To: {draft.to ?? "use the authority's website"}</p>
          <p className="mt-1 font-medium">{draft.subject}</p>
          <pre className="mt-2 max-h-64 overflow-auto whitespace-pre-wrap font-sans text-sm">{draft.body}</pre>
          <div className="mt-3 flex justify-end gap-2">
            <Button size="sm" variant="ghost" onClick={() => setDraft(null)}>Close</Button>
            <Button
              size="sm"
              onClick={async () => {
                await navigator.clipboard.writeText(`${draft.subject}\n\n${draft.body}`);
                setCopied(true);
                setTimeout(() => setCopied(false), 1500);
              }}
            >
              <Copy /> {copied ? "Copied" : "Copy"}
            </Button>
            {draft.to && draft.to.includes("@") ? (
              <Button size="sm" variant="primary" asChild>
                <a href={`mailto:${draft.to}?subject=${encodeURIComponent(draft.subject)}&body=${encodeURIComponent(draft.body)}`}>
                  <Mail /> Open in mail
                </a>
              </Button>
            ) : null}
          </div>
        </div>
      )}
    </div>
  );
}
