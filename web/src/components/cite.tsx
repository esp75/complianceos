"use client";

import { ExternalLink } from "lucide-react";
import { useState } from "react";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { formatDate } from "@/lib/dates";
import { segments } from "@/lib/timeline";
import type { Citation } from "@/lib/types";
import { safeHref } from "@/lib/links";
import { cn } from "@/lib/utils";

/** A citation chip; opens the quoted law with its official source. */
export function Cite({ id, citations, className }: { id: string; citations: Record<string, Citation>; className?: string }) {
  const c = citations[id];
  if (!c) {
    return <span className={cn("font-mono text-[0.7rem] text-muted-foreground", className)}>[{id}]</span>;
  }
  return (
    <Popover>
      <PopoverTrigger
        className={cn(
          "mx-0.5 inline-flex items-center rounded-sm border border-accent/25 bg-accent-soft px-1 py-px align-baseline font-mono text-[0.7rem] leading-tight text-accent hover:border-accent/60",
          className,
        )}
        aria-label={`Source: ${c.instrument}, ${c.provision}`}
      >
        {shortRef(c)}
      </PopoverTrigger>
      <PopoverContent>
        <CitationBody c={c} />
      </PopoverContent>
    </Popover>
  );
}

export function CitationBody({ c }: { c: Citation }) {
  const [original, setOriginal] = useState(false);
  const translated = c.language !== "en" && c.excerpt_en;
  return (
    <div className="space-y-2">
      <div>
        <p className="font-medium leading-snug">{c.instrument}</p>
        <p className="text-xs text-muted-foreground">{c.provision}</p>
      </div>
      <blockquote className="border-l-2 border-accent/40 pl-3 text-[0.8125rem] leading-relaxed">
        {translated && !original ? c.excerpt_en : c.excerpt}
      </blockquote>
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
        <a href={safeHref(c.url)} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-accent hover:underline">
          Official text <ExternalLink className="size-3" />
        </a>
        <span>Retrieved {formatDate(c.retrieved)}</span>
        {translated ? (
          <button type="button" className="underline underline-offset-2 hover:text-foreground" onClick={() => setOriginal(!original)}>
            {original ? "Show English (unofficial)" : `Show original (${c.language.toUpperCase()})`}
          </button>
        ) : null}
      </div>
    </div>
  );
}

function shortRef(c: Citation): string {
  const p = c.provision.replace(/^Article\s+/i, "Art. ").replace(/^Section\s+/i, "s. ").replace(/^No\.\s+/i, "No. ");
  const inst = c.instrument
    .replace(/^ITU Radio Regulations.*$/i, "RR")
    .replace(/^47 CFR Part 25.*$/i, "47 CFR")
    .replace(/^15 CFR Part 960.*$/i, "15 CFR")
    .replace(/^Code des postes et des communications électroniques$/i, "CPCE")
    .replace(/^Loi n° 2008-518.*$/i, "LOS")
    .replace(/^Loi du 15 décembre 2020.*$/i, "LU Space Law")
    .replace(/^Loi modifiée du 27 juillet 1991.*$/is, "LU Media Law");
  const short = `${inst} ${p}`.trim();
  return short.length > 42 ? `${short.slice(0, 40)}…` : short;
}

/** Text with inline [cite:id] markers rendered as chips. */
export function CitedText({ text, citations }: { text: string; citations: Record<string, Citation> }) {
  return (
    <>
      {segments(text).map((s, i) =>
        s.kind === "text" ? <span key={i}>{s.text}</span> : <Cite key={i} id={s.id} citations={citations} />,
      )}
    </>
  );
}
