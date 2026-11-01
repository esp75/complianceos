import useSWR, { type SWRConfiguration } from "swr";
import type {
  ApplicationEvent,
  Brief,
  Contact,
  ContactIn,
  DeadlineOut,
  EmailDraft,
  Facilitator,
  JurisdictionOut,
  Mission,
  MissionProfile,
  Recipients,
  Roadmap,
  TrackedApplication,
  WatchRun,
} from "./types";

/** Browser calls go to this origin; Next.js forwards /api/* to the planner API (next.config.mjs). */
export const API = "/api";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

async function detail(res: Response): Promise<string> {
  try {
    const body = (await res.json()) as { detail?: unknown };
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail)) {
      return body.detail
        .map((d: { loc?: unknown[]; msg?: string }) => `${(d.loc ?? []).slice(1).join(".")}: ${d.msg ?? ""}`)
        .join("; ");
    }
  } catch {
    /* not JSON */
  }
  return res.statusText || `HTTP ${res.status}`;
}

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API}${path}`, {
      ...init,
      // The custom header marks requests from this app; the API requires it for changes in local
      // mode, which other websites cannot send cross-site (CSRF protection).
      headers: { "Content-Type": "application/json", "X-ComplianceOS-Client": "web", ...(init?.headers ?? {}) },
    });
  } catch {
    throw new ApiError(0, "Can't reach the planner API. Check that it is running, then try again.");
  }
  if (!res.ok) throw new ApiError(res.status, await detail(res));
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

const fetcher = <T,>(path: string) => request<T>(path);

export function useApi<T>(path: string | null, config?: SWRConfiguration<T>) {
  return useSWR<T, ApiError>(path, fetcher, { revalidateOnFocus: false, ...config });
}

export type UsageKind = "session_start" | "mission_viewed" | "watch_viewed" | "alert_opened" | "dossier_exported";

/** Pilot usage (ADR-0021): which feature was used, never what it contained. Failures are ignored. */
export function recordUsage(kind: UsageKind): void {
  void request<void>("/usage", { method: "POST", body: JSON.stringify({ kind }) }).catch(() => undefined);
}

export const api = {
  missions: () => request<Mission[]>("/missions"),
  createMission: (profile: MissionProfile) =>
    request<Mission>("/missions", { method: "POST", body: JSON.stringify(profile) }),
  createSample: () => request<Mission>("/missions/sample", { method: "POST" }),
  updateMission: (id: string, profile: MissionProfile) =>
    request<Mission>(`/missions/${id}`, { method: "PUT", body: JSON.stringify(profile) }),
  deleteMission: (id: string) => request<void>(`/missions/${id}`, { method: "DELETE" }),
  preview: (profile: MissionProfile) =>
    request<Roadmap>("/roadmap", { method: "POST", body: JSON.stringify(profile) }),
  brief: (id: string, ai = false) =>
    request<Brief>(`/missions/${id}/brief${ai ? "?ai=true" : ""}`, { method: "POST" }),
  track: (missionId: string, licenseId: string) =>
    request<TrackedApplication>(`/missions/${missionId}/applications`, {
      method: "POST",
      body: JSON.stringify({ license_id: licenseId }),
    }),
  updateApplication: (id: string, patch: Record<string, unknown>) =>
    request<TrackedApplication>(`/applications/${id}`, { method: "PATCH", body: JSON.stringify(patch) }),
  addContact: (id: string, contact: ContactIn) =>
    request<Contact>(`/applications/${id}/contacts`, { method: "POST", body: JSON.stringify(contact) }),
  setRecipients: (recipients: string[]) =>
    request<Recipients>("/alerts/recipients", { method: "PUT", body: JSON.stringify({ recipients }) }),
  runWatch: () => request<WatchRun>("/watch/run", { method: "POST" }),
  introEmail: (missionId: string, licenseId: string, recipient: string) =>
    request<EmailDraft>(`/missions/${missionId}/intro-email`, {
      method: "POST",
      body: JSON.stringify({ license_id: licenseId, recipient }),
    }),
};

export const paths = {
  missions: "/missions",
  mission: (id: string) => `/missions/${id}`,
  roadmap: (id: string) => `/missions/${id}/roadmap`,
  applications: (id: string) => `/missions/${id}/applications`,
  deadlines: (id: string) => `/missions/${id}/deadlines`,
  watch: (id: string) => `/missions/${id}/watch`,
  events: (appId: string) => `/applications/${appId}/events`,
  contacts: (appId: string) => `/applications/${appId}/contacts`,
  recipients: "/alerts/recipients",
  usage: (days: number) => `/usage/summary?days=${days}`,
  jurisdictions: "/knowledge/jurisdictions",
  facilitators: "/knowledge/facilitators",
  calendar: (id: string) => `${API}/missions/${id}/calendar.ics`,
  dossier: (id: string) => `${API}/missions/${id}/dossier.pdf`,
  signedDossier: (id: string) => `${API}/missions/${id}/dossier.signed.json`,
  reviewPackage: (id: string) => `${API}/missions/${id}/dossier.md`,
};

export type { ApplicationEvent, Contact, DeadlineOut, Facilitator, JurisdictionOut };
