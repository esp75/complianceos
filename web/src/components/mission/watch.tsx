"use client";

import { ExternalLink, RefreshCw } from "lucide-react";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { formatDate } from "@/lib/dates";
import { STATUS } from "@/lib/labels";
import type { Roadmap, WatchItem } from "@/lib/types";

/** Changes in the public sources behind this mission's tracked applications (ADR-0019).
 *  The Watch says a source changed; it never says what the change means in law. */
export function Watch({ roadmap, items, onRun, onOpen }: {
  roadmap: Roadmap;
  items: WatchItem[];
  onRun: () => Promise<unknown>;
  onOpen: (licenseId: string) => void;
}) {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const names = Object.fromEntries(roadmap.items.map((i) => [i.license_id, i.name]));

  const check = async () => {
    setBusy(true);
    setMessage(null);
    try {
      const s = await api.runWatch();
      setMessage(`Checked ${s.checked} sources: ${s.changed} changed, ${s.published} newly published, ${s.unreachable} unreachable, ${s.unsupported} unreadable.`);
      await onRun();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "The check failed.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="max-w-2xl text-sm text-muted-foreground">
          The Watch re-checks the public sources the planner cites. A change means the source text differs
          from the last check: re-verify the cited provision before relying on it.
        </p>
        <Button size="sm" variant="ghost" onClick={check} disabled={busy}>
          <RefreshCw className={busy ? "animate-spin" : undefined} /> Check sources now
        </Button>
      </div>
      {message ? <p role="status" className="text-sm text-muted-foreground">{message}</p> : null}

      {items.length === 0 ? (
        <div className="rounded-lg border bg-surface p-6 text-sm text-muted-foreground">
          No changes to the sources behind your tracked applications.
        </div>
      ) : (
        <ul className="divide-y rounded-lg border bg-surface">
          {items.map(({ change: c, affected, jurisdictions, advice }) => (
            <li key={c.id} className="space-y-2 px-4 py-3 text-sm">
              <div className="flex flex-wrap items-center gap-2">
                <Badge tone={c.kind === "unreachable" ? "alarm" : "warn"}>
                  {c.kind === "changed" ? "Source changed" : c.kind === "published" ? "New publication" : "Source unreachable"}
                </Badge>
                <span className="text-xs tabular-nums text-muted-foreground">
                  detected {formatDate(c.detected_at)} · {jurisdictions.join(", ").toUpperCase()}
                </span>
              </div>
              <a
                href={c.url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex max-w-full items-center gap-1 break-all font-medium underline-offset-4 hover:underline"
              >
                {c.url} <ExternalLink className="size-3 shrink-0" />
              </a>
              {c.kind === "changed" ? (
                <>
                  <p className="text-xs text-muted-foreground">
                    +{c.words_added} / −{c.words_removed} words since the last check. {advice}
                  </p>
                  {c.ai_summary && (
                    <p className="text-xs text-muted-foreground">
                      AI-assisted triage ({c.materiality}, unverified): {c.ai_summary}
                    </p>
                  )}
                </>
              ) : c.kind === "published" ? (
                <p className="text-xs text-muted-foreground">
                  An official feed published: {c.detail}. Check whether it affects your application. {advice}
                </p>
              ) : (
                <p className="text-xs text-muted-foreground">{c.detail || "The source could not be fetched."} The last known text is kept.</p>
              )}
              <div className="flex flex-wrap gap-2">
                {affected.map((a) => (
                  <button
                    key={a.application_id}
                    type="button"
                    onClick={() => onOpen(a.license_id)}
                    className="flex items-center gap-2 rounded-md border px-2 py-1 text-xs hover:bg-muted/50"
                  >
                    {names[a.license_id] ?? a.license_id}
                    <Badge tone={STATUS[a.status].tone}>{STATUS[a.status].label}</Badge>
                  </button>
                ))}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
