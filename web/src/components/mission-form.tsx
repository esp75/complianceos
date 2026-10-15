"use client";

import { Check, ChevronLeft, ChevronRight, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Field, Input, Select } from "@/components/ui/field";
import { api } from "@/lib/api";
import { isoDate, today } from "@/lib/dates";
import { BANDS, COUNTRIES, ORBITS, SERVICES, countryName } from "@/lib/labels";
import type { FrequencyBand, MissionProfile, OrbitRegime, RadioService, Roadmap } from "@/lib/types";
import { cn } from "@/lib/utils";

const COVERED = ["FR", "GB", "LU", "US"];
const STEPS = ["Operator", "Spacecraft & orbit", "Spectrum & services", "Markets & launch"] as const;

export function emptyProfile(): MissionProfile {
  const launch = today();
  launch.setUTCFullYear(launch.getUTCFullYear() + 2);
  return {
    name: "",
    operator_name: "",
    operator_country: "",
    filing_administration: null,
    control_country: null,
    launch_country: null,
    ground_station_countries: [],
    service_countries: [],
    orbit: "LEO",
    altitude_km: 550,
    satellite_count: 1,
    services: ["space_operation"],
    frequency_bands: [],
    earth_observation_imaging: false,
    user_terminals: false,
    target_launch_date: isoDate(launch),
    service_start_date: null,
  };
}

function stepProblems(p: MissionProfile, step: number): string[] {
  const out: string[] = [];
  if (step === 0) {
    if (!p.name.trim()) out.push("Give the mission a name.");
    if (!p.operator_country) out.push("Choose the country where the operator is established.");
  }
  if (step === 1 && (!p.satellite_count || p.satellite_count < 1)) out.push("Enter at least one satellite.");
  if (step === 2 && p.services.length === 0) out.push("Choose at least one radio service.");
  if (step === 3 && !p.target_launch_date) out.push("Choose a target launch date.");
  return out;
}

export function MissionForm({
  initial,
  submitLabel,
  onSubmit,
}: {
  initial: MissionProfile;
  submitLabel: string;
  onSubmit: (p: MissionProfile) => Promise<void>;
}) {
  const [p, setP] = useState<MissionProfile>(initial);
  const [step, setStep] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState<Roadmap | null>(null);
  const set = <K extends keyof MissionProfile>(k: K, v: MissionProfile[K]) => setP((x) => ({ ...x, [k]: v }));
  const problems = stepProblems(p, step);

  const previewable = useMemo(() => Boolean(p.operator_country && p.services.length && p.target_launch_date), [p]);
  useEffect(() => {
    if (!previewable) return;
    const t = setTimeout(() => {
      api
        .preview({ ...p, name: p.name || "Draft mission" })
        .then(setPreview)
        .catch(() => setPreview(null));
    }, 350);
    return () => clearTimeout(t);
  }, [p, previewable]);

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      await onSubmit(p);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setBusy(false);
    }
  }

  return (
    <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_20rem]">
      <div>
        <ol className="mb-6 flex flex-wrap gap-2" aria-label="Steps">
          {STEPS.map((s, i) => (
            <li key={s}>
              <button
                type="button"
                onClick={() => setStep(i)}
                aria-current={i === step ? "step" : undefined}
                className={cn(
                  "flex items-center gap-2 rounded-full border px-3 py-1 text-sm",
                  i === step ? "border-accent bg-accent-soft text-accent" : "text-muted-foreground hover:bg-muted",
                )}
              >
                <span className="font-mono text-xs">{i + 1}</span> {s}
              </button>
            </li>
          ))}
        </ol>

        <Card className="p-5 sm:p-6">
          {step === 0 && (
            <div className="grid gap-5">
              <Field label="Mission name" htmlFor="name">
                <Input id="name" value={p.name} onChange={(e) => set("name", e.target.value)} placeholder="e.g. Pathfinder EO-1" />
              </Field>
              <Field label="Operator (company) name" htmlFor="op" hint="Used in the intro emails the planner drafts for you.">
                <Input id="op" value={p.operator_name ?? ""} onChange={(e) => set("operator_name", e.target.value)} />
              </Field>
              <Field
                label="Where is the operator established?"
                htmlFor="opc"
                hint="The country where the company is incorporated. Many space laws apply to their own nationals and companies wherever they operate."
              >
                <CountrySelect id="opc" value={p.operator_country} onChange={(v) => set("operator_country", v ?? "")} />
              </Field>
              <div className="grid gap-5 sm:grid-cols-2">
                <Field
                  label="Mission control location"
                  htmlFor="ctl"
                  hint="Where the satellites are commanded from, if different."
                >
                  <CountrySelect id="ctl" value={p.control_country ?? ""} onChange={(v) => set("control_country", v)} allowEmpty="Same as operator" />
                </Field>
                <Field
                  label="ITU filing administration"
                  htmlFor="adm"
                  hint="The country that files your frequencies with the ITU, if not your own."
                >
                  <CountrySelect id="adm" value={p.filing_administration ?? ""} onChange={(v) => set("filing_administration", v)} allowEmpty="Same as operator" />
                </Field>
              </div>
            </div>
          )}

          {step === 1 && (
            <div className="grid gap-5">
              <fieldset>
                <legend className="mb-2 text-sm font-medium">Orbit</legend>
                <div className="grid gap-2 sm:grid-cols-2">
                  {(Object.keys(ORBITS) as OrbitRegime[]).map((o) => (
                    <Choice key={o} selected={p.orbit === o} onClick={() => set("orbit", o)} title={ORBITS[o]} />
                  ))}
                </div>
              </fieldset>
              <div className="grid gap-5 sm:grid-cols-2">
                <Field label="Number of satellites" htmlFor="n" hint="Some routes (e.g. the FCC small-satellite process) depend on it.">
                  <Input id="n" type="number" min={1} value={p.satellite_count} onChange={(e) => set("satellite_count", Number(e.target.value))} />
                </Field>
                <Field label="Altitude (km)" htmlFor="alt" hint="Approximate operational altitude; leave empty if unknown.">
                  <Input
                    id="alt"
                    type="number"
                    min={1}
                    value={p.altitude_km ?? ""}
                    onChange={(e) => set("altitude_km", e.target.value === "" ? null : Number(e.target.value))}
                  />
                </Field>
              </div>
              <Toggle
                checked={p.earth_observation_imaging ?? false}
                onChange={(v) => set("earth_observation_imaging", v)}
                title="Imaging payload"
                hint="You collect and distribute Earth imagery. Some countries license remote sensing separately."
              />
            </div>
          )}

          {step === 2 && (
            <div className="grid gap-5">
              <fieldset>
                <legend className="mb-1 text-sm font-medium">Radio services</legend>
                <p className="mb-3 text-xs text-muted-foreground">What your satellites do with radio. This decides the ITU route (publication or coordination).</p>
                <div className="grid gap-2 sm:grid-cols-2">
                  {(Object.keys(SERVICES) as RadioService[]).map((s) => (
                    <Choice
                      key={s}
                      selected={p.services.includes(s)}
                      onClick={() => set("services", toggle(p.services, s))}
                      title={SERVICES[s].label}
                      hint={SERVICES[s].hint}
                      multi
                    />
                  ))}
                </div>
              </fieldset>
              <fieldset>
                <legend className="mb-1 text-sm font-medium">Frequency bands</legend>
                <p className="mb-3 text-xs text-muted-foreground">Rough band letters are enough at this stage.</p>
                <div className="flex flex-wrap gap-2">
                  {BANDS.map((b) => (
                    <Chip key={b} selected={(p.frequency_bands ?? []).includes(b)} onClick={() => set("frequency_bands", toggle(p.frequency_bands ?? [], b as FrequencyBand))}>
                      {b}
                    </Chip>
                  ))}
                </div>
              </fieldset>
            </div>
          )}

          {step === 3 && (
            <div className="grid gap-5">
              <Field label="Countries where you will serve customers" hint="Serving a market often needs a local authorisation (market access or landing rights).">
                <CountryList value={p.service_countries ?? []} onChange={(v) => set("service_countries", v)} />
              </Field>
              <Field label="Ground station countries" hint="Earth stations are licensed where they stand.">
                <CountryList value={p.ground_station_countries ?? []} onChange={(v) => set("ground_station_countries", v)} />
              </Field>
              <div className="grid gap-5 sm:grid-cols-2">
                <Field label="Launch site country" htmlFor="lc" hint="Leave as not decided if you have no launch contract yet.">
                  <CountrySelect id="lc" value={p.launch_country ?? ""} onChange={(v) => set("launch_country", v)} allowEmpty="Not decided yet" />
                </Field>
                <Field label="Target launch date" htmlFor="ld" hint="The roadmap works back from this date.">
                  <Input id="ld" type="date" value={p.target_launch_date} onChange={(e) => set("target_launch_date", e.target.value)} />
                </Field>
              </div>
              <Toggle
                checked={p.user_terminals ?? false}
                onChange={(v) => set("user_terminals", v)}
                title="End-user terminals"
                hint="Customers use your terminals in the service countries."
              />
            </div>
          )}

          {problems.length > 0 ? (
            <ul className="mt-5 space-y-1 text-sm text-warn">
              {problems.map((x) => (
                <li key={x}>{x}</li>
              ))}
            </ul>
          ) : null}
          {error ? <p className="mt-5 text-sm text-alarm">{error}</p> : null}

          <div className="mt-6 flex items-center justify-between border-t pt-5">
            <Button variant="ghost" onClick={() => setStep(step - 1)} disabled={step === 0}>
              <ChevronLeft /> Back
            </Button>
            {step < STEPS.length - 1 ? (
              <Button variant="primary" onClick={() => setStep(step + 1)} disabled={problems.length > 0}>
                Next <ChevronRight />
              </Button>
            ) : (
              <Button variant="primary" onClick={submit} disabled={busy || STEPS.some((_, i) => stepProblems(p, i).length > 0)}>
                <Check /> {busy ? "Saving…" : submitLabel}
              </Button>
            )}
          </div>
        </Card>
      </div>

      <aside className="lg:sticky lg:top-20 lg:self-start" aria-live="polite">
        <Card className="p-5">
          <h2 className="text-sm font-semibold">Live preview</h2>
          {!previewable || !preview ? (
            <p className="mt-2 text-sm text-muted-foreground">Choose the operator country and a radio service to see what applies.</p>
          ) : (
            <>
              <p className="mt-2 text-2xl font-semibold tabular-nums">{preview.items.length}</p>
              <p className="text-sm text-muted-foreground">
                licences and filings across {preview.jurisdictions.length} jurisdiction{preview.jurisdictions.length === 1 ? "" : "s"}
              </p>
              <ul className="mt-4 space-y-3 text-sm">
                {preview.jurisdictions.map((j) => (
                  <li key={j.id}>
                    <p className="font-medium">{j.name}</p>
                    <ul className="mt-1 space-y-0.5 text-muted-foreground">
                      {preview.items
                        .filter((i) => i.jurisdiction === j.id)
                        .map((i) => (
                          <li key={i.license_id} className="flex items-start gap-2">
                            <span className={cn("mt-1.5 size-1.5 shrink-0 rounded-full", i.risk === "late" ? "bg-alarm" : i.critical ? "bg-accent" : "bg-muted-foreground/40")} />
                            {i.name}
                          </li>
                        ))}
                    </ul>
                  </li>
                ))}
              </ul>
              {preview.warnings.length ? (
                <div className="mt-4 space-y-1 border-t pt-3 text-xs text-muted-foreground">
                  {preview.warnings.map((w) => (
                    <p key={w}>{w}</p>
                  ))}
                </div>
              ) : null}
            </>
          )}
        </Card>
      </aside>
    </div>
  );
}

function toggle<T>(list: T[], v: T): T[] {
  return list.includes(v) ? list.filter((x) => x !== v) : [...list, v];
}

function Choice({ selected, onClick, title, hint, multi }: { selected: boolean; onClick: () => void; title: string; hint?: string; multi?: boolean }) {
  return (
    <button
      type="button"
      role={multi ? "checkbox" : "radio"}
      aria-checked={selected}
      onClick={onClick}
      className={cn(
        "flex items-start gap-3 rounded-md border p-3 text-left transition-colors",
        selected ? "border-accent bg-accent-soft" : "hover:bg-muted",
      )}
    >
      <span className={cn("mt-0.5 flex size-4 shrink-0 items-center justify-center border", multi ? "rounded-sm" : "rounded-full", selected ? "border-accent bg-accent text-accent-foreground" : "border-muted-foreground/40")}>
        {selected ? <Check className="size-3" /> : null}
      </span>
      <span>
        <span className="block text-sm font-medium">{title}</span>
        {hint ? <span className="mt-0.5 block text-xs text-muted-foreground">{hint}</span> : null}
      </span>
    </button>
  );
}

function Chip({ selected, onClick, children }: { selected: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      type="button"
      aria-pressed={selected}
      onClick={onClick}
      className={cn("rounded-sm border px-2.5 py-1 font-mono text-xs", selected ? "border-accent bg-accent text-accent-foreground" : "hover:bg-muted")}
    >
      {children}
    </button>
  );
}

function Toggle({ checked, onChange, title, hint }: { checked: boolean; onChange: (v: boolean) => void; title: string; hint: string }) {
  return <Choice selected={checked} onClick={() => onChange(!checked)} title={title} hint={hint} multi />;
}

const SORTED = Object.entries(COUNTRIES).sort((a, b) => a[1].localeCompare(b[1]));

function CountrySelect({ id, value, onChange, allowEmpty }: { id: string; value: string; onChange: (v: string | null) => void; allowEmpty?: string }) {
  return (
    <Select id={id} value={value} onChange={(e) => onChange(e.target.value || null)}>
      <option value="">{allowEmpty ?? "Choose a country…"}</option>
      <optgroup label="Covered by the data">
        {COVERED.map((c) => (
          <option key={c} value={c}>
            {countryName(c)}
          </option>
        ))}
      </optgroup>
      <optgroup label="Other countries">
        {SORTED.filter(([c]) => !COVERED.includes(c)).map(([c, n]) => (
          <option key={c} value={c}>
            {n}
          </option>
        ))}
      </optgroup>
    </Select>
  );
}

function CountryList({ value, onChange }: { value: string[]; onChange: (v: string[]) => void }) {
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-2">
        {value.map((c) => (
          <Badge key={c} tone="outline" className="gap-1.5 py-1 pl-2 pr-1 text-sm">
            {countryName(c)}
            <button type="button" onClick={() => onChange(value.filter((x) => x !== c))} aria-label={`Remove ${countryName(c)}`} className="rounded-sm p-0.5 hover:bg-muted">
              <X className="size-3" />
            </button>
          </Badge>
        ))}
        {value.length === 0 ? <span className="text-sm text-muted-foreground">None yet</span> : null}
      </div>
      <div className="flex flex-wrap items-center gap-2">
        {COVERED.filter((c) => !value.includes(c)).map((c) => (
          <button key={c} type="button" onClick={() => onChange([...value, c])} className="rounded-sm border border-dashed px-2 py-0.5 text-xs text-muted-foreground hover:border-accent hover:text-accent">
            + {countryName(c)}
          </button>
        ))}
        <Select
          aria-label="Add another country"
          className="h-8 w-auto text-xs"
          value=""
          onChange={(e) => e.target.value && onChange([...value, e.target.value])}
        >
          <option value="">Add another country…</option>
          {SORTED.filter(([c]) => !value.includes(c) && !COVERED.includes(c)).map(([c, n]) => (
            <option key={c} value={c}>
              {n}
            </option>
          ))}
        </Select>
      </div>
    </div>
  );
}
