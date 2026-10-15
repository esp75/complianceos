import Link from "next/link";
import { ThemeToggle } from "./theme-toggle";

const NAV = [
  { href: "/", label: "Missions" },
  { href: "/directory", label: "Directory" },
  { href: "/data", label: "Data & sources" },
];

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-30 border-b bg-background/90 backdrop-blur">
      <div className="container flex h-14 items-center gap-2 sm:gap-6">
        <Link href="/" className="flex shrink-0 items-center gap-2 font-semibold tracking-tight" aria-label="ComplianceOS home">
          <Logo />
          <span className="hidden sm:inline">ComplianceOS</span>
        </Link>
        <nav className="flex min-w-0 items-center gap-0.5 overflow-x-auto text-sm sm:gap-1" aria-label="Main">
          {NAV.map((n) => (
            <Link key={n.href} href={n.href} className="whitespace-nowrap rounded-sm px-2 py-1.5 text-muted-foreground hover:bg-muted hover:text-foreground sm:px-2.5">
              {n.label}
            </Link>
          ))}
        </nav>
        <div className="ml-auto flex items-center gap-1">
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}

function Logo() {
  return (
    <svg viewBox="0 0 24 24" className="size-6 text-accent" aria-hidden="true">
      <circle cx="12" cy="12" r="3.2" fill="currentColor" />
      <ellipse cx="12" cy="12" rx="10" ry="4.2" fill="none" stroke="currentColor" strokeWidth="1.6" transform="rotate(-28 12 12)" />
    </svg>
  );
}
