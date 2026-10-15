"use client";

import Link from "next/link";
import { ApiNotice } from "@/components/api-notice";
import { Badge } from "@/components/ui/badge";
import { paths, useApi } from "@/lib/api";
import { formatDate } from "@/lib/dates";
import { REPO_URL } from "@/lib/site";
import type { JurisdictionOut } from "@/lib/types";

export default function DataPage() {
  const js = useApi<JurisdictionOut[]>(paths.jurisdictions);
  return (
    <div className="container max-w-4xl py-8">
      <h1 className="text-2xl font-semibold tracking-tight">Data &amp; sources</h1>
      <p className="mt-2 text-muted-foreground">
        The planner reasons over an open dataset kept in the repository under <code className="font-mono text-sm">knowledge/</code>.
        Every requirement cites the text of the law, with the official URL and the date it was checked. Nothing is
        generated at request time.
      </p>
      <ApiNotice error={js.error} />

      <section className="mt-8">
        <h2 className="text-lg font-semibold">Coverage</h2>
        <div className="mt-3 overflow-x-auto rounded-lg border bg-surface">
          <table className="w-full text-sm">
            <thead className="border-b text-left text-xs text-muted-foreground">
              <tr>
                <th className="px-4 py-2 font-medium">Jurisdiction</th>
                <th className="px-4 py-2 font-medium">Licences &amp; filings</th>
                <th className="px-4 py-2 font-medium">Status</th>
                <th className="px-4 py-2 font-medium">Last verified</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {(js.data ?? []).map(({ jurisdiction: j, licenses }) => (
                <tr key={j.id}>
                  <td className="px-4 py-2.5 font-medium">{j.name}</td>
                  <td className="px-4 py-2.5 tabular-nums">{licenses.length}</td>
                  <td className="px-4 py-2.5">{j.status === "draft" ? <Badge tone="dashed">Draft</Badge> : <Badge tone="ok">Reviewed</Badge>}</td>
                  <td className="px-4 py-2.5 tabular-nums">{formatDate(j.last_verified)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="mt-10 space-y-3 text-sm leading-relaxed">
        <h2 className="text-lg font-semibold">How the data is checked</h2>
        <p>
          <strong>Draft</strong> means researched from official sources (legislation portals, official journals, regulators&apos;
          own guidance) with each quoted excerpt checked against the source text. <strong>Reviewed</strong> means a
          licensing practitioner has also checked it. Durations are labelled <em>statutory</em> (a limit set in law),{" "}
          <em>published practice</em> (the authority&apos;s guidance) or <em>estimate</em> (no official figure).
        </p>
        <p>
          Where a site could not be read automatically, the verification log in the repository says so, and lists what
          still needs a human. Countries without data are named in your roadmap&apos;s warnings rather than left out.
        </p>
      </section>

      <section id="contribute" className="mt-10 space-y-3 text-sm leading-relaxed">
        <h2 className="text-lg font-semibold">Contribute or correct</h2>
        <ol className="list-inside list-decimal space-y-1.5">
          <li>Each licence is one YAML file: who needs it (a small rule), why (with citations), timing, documents, fees and duties that follow.</li>
          <li>Quote the law from the official publisher, with the URL and date. Never cite from memory.</li>
          <li>Run <code className="font-mono">uv run python -m app.planner.knowledge validate</code>; it reports every problem at once.</li>
          <li>Open a pull request. Practitioners can mark records as reviewed.</li>
        </ol>
        {REPO_URL ? (
          <p>
            <a href={REPO_URL} className="text-accent hover:underline">Repository and contributing guide →</a>
          </p>
        ) : (
          <p className="text-muted-foreground">See CONTRIBUTING.md in the repository.</p>
        )}
      </section>

      <section className="mt-10 space-y-2 text-sm leading-relaxed">
        <h2 className="text-lg font-semibold">Licences</h2>
        <p>
          Software: Apache-2.0. Dataset: CC BY 4.0 for our summaries, rules and translations. Quoted legal excerpts keep
          their publishers&apos; terms (UK Crown copyright, US Government works, French and Luxembourg official texts,
          ITU Radio Regulations © ITU, quoted briefly with attribution).
        </p>
        <p className="text-muted-foreground">
          Information, not legal advice. <Link href="/" className="underline underline-offset-2">Back to missions</Link>
        </p>
      </section>
    </div>
  );
}
