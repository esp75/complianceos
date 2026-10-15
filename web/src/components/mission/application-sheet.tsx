"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Field, Input, Select, Textarea } from "@/components/ui/field";
import { Sheet, SheetContent } from "@/components/ui/sheet";
import { api, paths, useApi } from "@/lib/api";
import { formatDate, isoDate, relative, today } from "@/lib/dates";
import { NEXT_STATUS, STATUS } from "@/lib/labels";
import type { AppStatus, ApplicationEvent, Contact, ContactIn, TrackedApplication } from "@/lib/types";

export function ApplicationSheet({
  tracked,
  onClose,
  onChanged,
  onOpenLicense,
}: {
  tracked: TrackedApplication | null;
  onClose: () => void;
  onChanged: () => void;
  onOpenLicense: (licenseId: string) => void;
}) {
  return (
    <Sheet open={tracked !== null} onOpenChange={(o) => !o && onClose()}>
      {tracked ? (
        <SheetContent
          title={tracked.item?.name ?? tracked.application.license_id}
          description={
            <span className="flex flex-wrap items-center gap-2">
              <Badge tone={STATUS[tracked.application.status].tone}>{STATUS[tracked.application.status].label}</Badge>
              <button type="button" className="text-accent hover:underline" onClick={() => onOpenLicense(tracked.application.license_id)}>
                Requirement details
              </button>
            </span>
          }
        >
          <Body key={tracked.application.id + tracked.application.updated_at} tracked={tracked} onChanged={onChanged} />
        </SheetContent>
      ) : null}
    </Sheet>
  );
}

function Body({ tracked, onChanged }: { tracked: TrackedApplication; onChanged: () => void }) {
  const a = tracked.application;
  const events = useApi<ApplicationEvent[]>(paths.events(a.id));
  const contacts = useApi<Contact[]>(paths.contacts(a.id));
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState<AppStatus | null>(null);
  const [date, setDate] = useState(isoDate(today()));
  const [note, setNote] = useState("");
  const [reference, setReference] = useState(a.reference ?? "");
  const [notes, setNotes] = useState(a.notes ?? "");

  async function patch(body: Record<string, unknown>) {
    setError(null);
    try {
      await api.updateApplication(a.id, body);
      await Promise.all([events.mutate(), contacts.mutate()]);
      onChanged();
      setPending(null);
      setNote("");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  const needsDate = (s: AppStatus) => s === "submitted" || s === "granted";

  return (
    <div className="space-y-7 text-sm">
      <div className={`rounded-md border p-3 ${tracked.next_action.overdue ? "border-alarm/50 bg-alarm-soft" : "bg-surface"}`}>
        <p className="text-xs text-muted-foreground">Next action</p>
        <p className="font-medium">{tracked.next_action.title}</p>
        {tracked.next_action.due ? (
          <p className="text-xs text-muted-foreground">
            {formatDate(tracked.next_action.due)} · {relative(tracked.next_action.due)}
          </p>
        ) : null}
      </div>

      <section>
        <h3 className="mb-2.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">Update status</h3>
        {NEXT_STATUS[a.status].length === 0 ? (
          <p className="text-muted-foreground">This application is granted. Its obligations now appear under Deadlines.</p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {NEXT_STATUS[a.status].map((s) => (
              <Button key={s} size="sm" variant={pending === s ? "primary" : "secondary"} onClick={() => setPending(s)}>
                {STATUS[s].label}
              </Button>
            ))}
          </div>
        )}
        {pending ? (
          <div className="mt-3 grid gap-3 rounded-md border bg-surface p-3 sm:grid-cols-[10rem_1fr_auto] sm:items-end">
            {needsDate(pending) ? (
              <Field label={pending === "submitted" ? "Submitted on" : "Granted on"} htmlFor="d">
                <Input id="d" type="date" value={date} max={isoDate(today())} onChange={(e) => setDate(e.target.value)} />
              </Field>
            ) : (
              <span />
            )}
            <Field label="Note (optional)" htmlFor="n">
              <Input id="n" value={note} onChange={(e) => setNote(e.target.value)} placeholder="e.g. filed by email, ref. in thread" />
            </Field>
            <Button
              variant="primary"
              onClick={() =>
                patch({
                  status: pending,
                  note,
                  ...(pending === "submitted" ? { submitted_on: date } : {}),
                  ...(pending === "granted" ? { granted_on: date } : {}),
                })
              }
            >
              Save
            </Button>
          </div>
        ) : null}
        {error ? <p className="mt-2 text-alarm">{error}</p> : null}
        <dl className="mt-4 grid grid-cols-2 gap-3">
          <div>
            <dt className="text-xs text-muted-foreground">Submitted</dt>
            <dd>{formatDate(a.submitted_on)}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">Granted</dt>
            <dd>{formatDate(a.granted_on)}</dd>
          </div>
        </dl>
      </section>

      <section className="grid gap-3">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Reference and notes</h3>
        <Field label="Authority reference" htmlFor="ref">
          <Input id="ref" value={reference} onChange={(e) => setReference(e.target.value)} placeholder="File or case number" />
        </Field>
        <Field label="Notes" htmlFor="notes">
          <Textarea id="notes" value={notes} onChange={(e) => setNotes(e.target.value)} />
        </Field>
        <div>
          <Button size="sm" disabled={reference === (a.reference ?? "") && notes === (a.notes ?? "")} onClick={() => patch({ reference, notes })}>
            Save notes
          </Button>
        </div>
      </section>

      <ContactLog appId={a.id} contacts={contacts.data ?? []} onAdded={async () => { await Promise.all([contacts.mutate(), events.mutate()]); onChanged(); }} />

      <section>
        <h3 className="mb-2.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">History</h3>
        <ol className="space-y-2 border-l pl-4">
          {(events.data ?? []).map((e) => (
            <li key={e.id} className="relative">
              <span className="absolute -left-[1.3rem] top-1.5 size-2 rounded-full border bg-surface" />
              <p>
                {e.kind === "created" && "Tracking started"}
                {e.kind === "status" && (
                  <>
                    {e.from_status ? STATUS[e.from_status].label : "—"} → <span className="font-medium">{e.to_status ? STATUS[e.to_status].label : ""}</span>
                  </>
                )}
                {e.kind === "update" && "Details updated"}
                {e.kind === "contact" && <>Contact logged: {e.note}</>}
                {e.note && e.kind !== "contact" ? <span className="text-muted-foreground"> — {e.note}</span> : null}
              </p>
              <p className="text-xs text-muted-foreground">{new Date(e.at).toLocaleString("en-GB", { dateStyle: "medium", timeStyle: "short" })}</p>
            </li>
          ))}
        </ol>
      </section>
    </div>
  );
}

const CHANNELS: ContactIn["channel"][] = ["email", "phone", "meeting", "letter", "web_form", "portal", "other"];

function ContactLog({ appId, contacts, onAdded }: { appId: string; contacts: Contact[]; onAdded: () => Promise<void> }) {
  const empty = (): ContactIn => ({ on_date: isoDate(today()), channel: "email", counterpart: "", summary: "", next_step: "", next_step_due: null });
  const [form, setForm] = useState<ContactIn>(empty());
  const [open, setOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  return (
    <section>
      <div className="mb-2.5 flex items-center justify-between">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Conversations</h3>
        {!open ? (
          <Button size="sm" variant="ghost" onClick={() => setOpen(true)}>
            Log a contact
          </Button>
        ) : null}
      </div>
      {open ? (
        <form
          className="mb-4 grid gap-3 rounded-md border bg-surface p-3 sm:grid-cols-2"
          onSubmit={async (e) => {
            e.preventDefault();
            setError(null);
            try {
              await api.addContact(appId, { ...form, next_step_due: form.next_step_due || null });
              setForm(empty());
              setOpen(false);
              await onAdded();
            } catch (err) {
              setError(err instanceof Error ? err.message : String(err));
            }
          }}
        >
          <Field label="Date" htmlFor="cd">
            <Input id="cd" type="date" value={form.on_date} onChange={(e) => setForm({ ...form, on_date: e.target.value })} required />
          </Field>
          <Field label="Channel" htmlFor="cc">
            <Select id="cc" value={form.channel} onChange={(e) => setForm({ ...form, channel: e.target.value as ContactIn["channel"] })}>
              {CHANNELS.map((c) => (
                <option key={c} value={c}>
                  {c.replace("_", " ")}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="With" htmlFor="cw" className="sm:col-span-2">
            <Input id="cw" value={form.counterpart} onChange={(e) => setForm({ ...form, counterpart: e.target.value })} placeholder="Authority, department or firm" required />
          </Field>
          <Field label="What was said" htmlFor="cs" className="sm:col-span-2">
            <Textarea id="cs" value={form.summary} onChange={(e) => setForm({ ...form, summary: e.target.value })} required />
          </Field>
          <Field label="Next step" htmlFor="cn">
            <Input id="cn" value={form.next_step ?? ""} onChange={(e) => setForm({ ...form, next_step: e.target.value })} />
          </Field>
          <Field label="Next step due" htmlFor="cnd">
            <Input id="cnd" type="date" value={form.next_step_due ?? ""} onChange={(e) => setForm({ ...form, next_step_due: e.target.value || null })} />
          </Field>
          {error ? <p className="text-alarm sm:col-span-2">{error}</p> : null}
          <div className="flex justify-end gap-2 sm:col-span-2">
            <Button type="button" variant="ghost" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary">
              Save contact
            </Button>
          </div>
        </form>
      ) : null}
      {contacts.length === 0 ? (
        <p className="text-muted-foreground">No conversations logged yet.</p>
      ) : (
        <ul className="space-y-3">
          {[...contacts].reverse().map((c) => (
            <li key={c.id} className="rounded-md border bg-surface p-3">
              <p className="text-xs text-muted-foreground">
                {formatDate(c.on_date)} · {c.channel.replace("_", " ")} · {c.counterpart}
              </p>
              <p className="mt-1 whitespace-pre-wrap">{c.summary}</p>
              {c.next_step ? (
                <p className="mt-2 text-xs">
                  <span className="font-medium">Next:</span> {c.next_step}
                  {c.next_step_due ? ` — ${formatDate(c.next_step_due)} (${relative(c.next_step_due)})` : ""}
                </p>
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
