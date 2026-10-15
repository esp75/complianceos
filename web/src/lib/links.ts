/** Only these schemes are ever rendered as links from data (defense in depth: the knowledge
 * validator already restricts contact values by kind). */
const SAFE = /^(https?:|mailto:|tel:)/i;

export function safeHref(href: string | null | undefined): string | undefined {
  if (!href) return undefined;
  const v = href.trim();
  return SAFE.test(v) ? v : undefined;
}

export function contactHref(kind: string, value: string): string | undefined {
  if (kind === "email") return safeHref(`mailto:${value}`);
  if (kind === "phone") return safeHref(`tel:${value.replace(/\s/g, "")}`);
  if (kind === "postal") return undefined;
  return safeHref(value);
}
