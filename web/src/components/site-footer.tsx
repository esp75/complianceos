import Link from "next/link";

export function SiteFooter() {
  return (
    <footer className="mt-16 border-t">
      <div className="container flex flex-col gap-2 py-6 text-xs text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
        <p className="max-w-2xl">
          Information, not legal advice. Every requirement links to the law it comes from and says when it was last
          checked. Confirm with the competent authority before acting.
        </p>
        <p className="shrink-0">
          Open source · <Link href="/data" className="underline underline-offset-2 hover:text-foreground">data & licences</Link>
        </p>
      </div>
    </footer>
  );
}
