/** Public repository URL, used for "suggest a correction" links. Set NEXT_PUBLIC_REPO_URL when the
 * repository is published; without it, correction links point to the in-app data page. */
export const REPO_URL = process.env.NEXT_PUBLIC_REPO_URL ?? "";

export function correctionUrl(subject: string): string {
  if (!REPO_URL) return "/data#contribute";
  const title = encodeURIComponent(`Data correction: ${subject}`);
  return `${REPO_URL}/issues/new?template=data-correction.yml&title=${title}`;
}
