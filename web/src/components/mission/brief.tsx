"use client";

import { Sparkles } from "lucide-react";
import { useEffect, useState } from "react";
import { CitedText } from "@/components/cite";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ApiError, api } from "@/lib/api";
import type { Brief } from "@/lib/types";

export function BriefView({ missionId, version }: { missionId: string; version: string }) {
  const [brief, setBrief] = useState<Brief | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setBrief(null);
    api.brief(missionId).then(setBrief).catch((e) => setError(String(e?.message ?? e)));
  }, [missionId, version]);

  async function withClaude() {
    setBusy(true);
    setError(null);
    try {
      setBrief(await api.brief(missionId, true));
    } catch (e) {
      if (e instanceof ApiError && e.status === 503) setError("No Claude API key is configured on this server, so the summary stays deterministic.");
      else if (e instanceof ApiError && e.status === 422) setError(`Claude's draft was rejected because it did not cite the law correctly (${e.message}). The deterministic summary is shown instead.`);
      else setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  if (!brief) return <p className="text-sm text-muted-foreground">{error ?? "Preparing the brief…"}</p>;
  return (
    <article className="max-w-3xl space-y-8">
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border bg-surface p-4 text-sm">
        <p className="text-muted-foreground">
          {brief.mode === "llm"
            ? "Summary written by Claude from the roadmap, checked against its citations. Every other section is generated from the data."
            : "Generated from the roadmap data. Every legal statement is cited; click a reference to read the law."}
        </p>
        <Button size="sm" onClick={withClaude} disabled={busy}>
          <Sparkles /> {busy ? "Writing…" : "Rewrite summary with Claude"}
        </Button>
      </div>
      {error ? <p className="text-sm text-warn">{error}</p> : null}
      {brief.sections.map((s) =>
        s.paragraphs.length ? (
          <section key={s.id}>
            <h2 className="mb-3 flex items-center gap-2 text-lg font-semibold">
              {s.title}
              {s.id === "summary" && brief.mode === "llm" ? <Badge tone="accent">Claude</Badge> : null}
            </h2>
            <div className="space-y-3 text-[0.9375rem] leading-relaxed">
              {s.paragraphs.map((p, n) => (
                <p key={n}>
                  <CitedText text={p} citations={brief.citations} />
                </p>
              ))}
            </div>
          </section>
        ) : null,
      )}
    </article>
  );
}
