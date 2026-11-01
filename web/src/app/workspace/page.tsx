"use client";

import { useEffect, useState } from "react";
import { ApiNotice } from "@/components/api-notice";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Field, Select, Textarea } from "@/components/ui/field";
import { api, paths, useApi } from "@/lib/api";
import type { Recipients, UsageSummary } from "@/lib/types";

/** What each usage event means in plain words. The planner stores the kind only, never content. */
const KINDS: [string, string][] = [
  ["session_start", "Opened the planner"],
  ["mission_viewed", "Viewed a mission"],
  ["watch_viewed", "Looked at the Watch tab"],
  ["alert_opened", "Came in from an alert email"],
  ["dossier_exported", "Exported a dossier or review package"],
];

export default function WorkspacePage() {
  return (
    <div className="container max-w-3xl space-y-8 py-10">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Workspace</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Who hears about source changes, and how this workspace has been used.
        </p>
      </div>
      <AlertRecipients />
      <UsageReport />
    </div>
  );
}

function AlertRecipients() {
  const { data, error, mutate } = useApi<Recipients>(paths.recipients);
  const [text, setText] = useState("");
  const [state, setState] = useState<{ kind: "idle" | "saving" | "saved" | "error"; msg?: string }>({ kind: "idle" });

  useEffect(() => {
    if (data) setText(data.recipients.join("\n"));
  }, [data]);

  async function save() {
    setState({ kind: "saving" });
    const list = text.split(/[\n,;]+/).map((s) => s.trim()).filter(Boolean);
    try {
      await mutate(await api.setRecipients(list), { revalidate: false });
      setState({ kind: "saved" });
    } catch (e) {
      setState({ kind: "error", msg: e instanceof Error ? e.message : String(e) });
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Watch alert recipients</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <ApiNotice error={error} />
        <Field
          label="Email addresses"
          htmlFor="recipients"
          hint={
            data?.fallback_to_deployment_list
              ? "None set for this workspace, so the deployment's default list receives your alerts. Set your own to change that."
              : "One per line. Only these addresses receive this workspace's alerts. Up to 20."
          }
        >
          <Textarea id="recipients" value={text} onChange={(e) => setText(e.target.value)} placeholder="regulatory@yourcompany.eu" rows={4} />
        </Field>
        <div className="flex items-center gap-3">
          <Button variant="primary" size="sm" onClick={save} disabled={state.kind === "saving"}>
            {state.kind === "saving" ? "Saving…" : "Save recipients"}
          </Button>
          {state.kind === "saved" ? <span role="status" className="text-sm text-muted-foreground">Saved.</span> : null}
          {state.kind === "error" ? <span role="alert" className="text-sm text-alarm">{state.msg}</span> : null}
        </div>
      </CardContent>
    </Card>
  );
}

function UsageReport() {
  const [days, setDays] = useState(30);
  const { data, error } = useApi<UsageSummary>(paths.usage(days));
  const total = data ? Object.values(data.counts).reduce((a, b) => a + b, 0) : 0;

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between gap-3">
        <CardTitle>Usage</CardTitle>
        <Select aria-label="Period" value={days} onChange={(e) => setDays(Number(e.target.value))} className="w-36">
          <option value={7}>Last 7 days</option>
          <option value={30}>Last 30 days</option>
          <option value={90}>Last 90 days</option>
        </Select>
      </CardHeader>
      <CardContent className="space-y-4">
        <ApiNotice error={error} />
        {data ? (
          <>
            <p className="text-sm text-muted-foreground">
              Active on <strong className="text-foreground">{data.active_days}</strong> of the last {data.days} days,{" "}
              {total} recorded actions. Only the kind of action is recorded, never what it contained.
            </p>
            <table className="w-full text-sm">
              <tbody>
                {KINDS.map(([kind, label]) => (
                  <tr key={kind} className="border-t">
                    <td className="py-2">{label}</td>
                    <td className="py-2 text-right tabular-nums">{data.counts[kind] ?? 0}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        ) : null}
      </CardContent>
    </Card>
  );
}
