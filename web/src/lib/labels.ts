/** Human-readable labels for API enums. Kept in one place so the UI can be translated later. */
import type { AppStatus, FrequencyBand, OrbitRegime, RadioService } from "./types";

export const COUNTRIES: Record<string, string> = {
  AR: "Argentina", AT: "Austria", AU: "Australia", BE: "Belgium", BR: "Brazil", CA: "Canada",
  CH: "Switzerland", CL: "Chile", CN: "China", CZ: "Czechia", DE: "Germany", DK: "Denmark",
  EE: "Estonia", ES: "Spain", FI: "Finland", FR: "France", GB: "United Kingdom", GR: "Greece",
  ID: "Indonesia", IE: "Ireland", IL: "Israel", IN: "India", IT: "Italy", JP: "Japan", KE: "Kenya",
  KR: "South Korea", LT: "Lithuania", LU: "Luxembourg", MX: "Mexico", MY: "Malaysia", NG: "Nigeria",
  NL: "Netherlands", NO: "Norway", NZ: "New Zealand", PE: "Peru", PH: "Philippines", PL: "Poland",
  PT: "Portugal", RO: "Romania", RW: "Rwanda", SA: "Saudi Arabia", SE: "Sweden", SG: "Singapore",
  TH: "Thailand", TR: "Türkiye", AE: "United Arab Emirates", UA: "Ukraine", US: "United States",
  VN: "Viet Nam", ZA: "South Africa",
};

export const countryName = (code: string | null | undefined) => (code ? COUNTRIES[code] ?? code : "—");

export const ORBITS: Record<OrbitRegime, string> = {
  LEO: "Low Earth orbit (LEO)",
  MEO: "Medium Earth orbit (MEO)",
  GEO: "Geostationary orbit (GEO)",
  HEO: "Highly elliptical orbit (HEO)",
};

export const SERVICES: Record<RadioService, { label: string; hint: string }> = {
  earth_exploration_satellite: { label: "Earth observation", hint: "Imaging, radar, environmental sensing (EESS)" },
  fixed_satellite: { label: "Fixed-satellite (broadband, backhaul)", hint: "Fixed earth stations and terminals (FSS)" },
  mobile_satellite: { label: "Mobile-satellite (IoT, direct-to-device)", hint: "Moving terminals, IoT (MSS)" },
  broadcasting_satellite: { label: "Broadcasting-satellite", hint: "Direct TV / radio (BSS)" },
  space_operation: { label: "Telemetry, tracking & command", hint: "Your TT&C links (space operation service)" },
  space_research: { label: "Space research", hint: "Science and technology missions" },
  amateur_satellite: { label: "Amateur-satellite", hint: "Amateur radio missions" },
  radionavigation_satellite: { label: "Radionavigation-satellite", hint: "Navigation and timing (RNSS)" },
};

export const BANDS: FrequencyBand[] = ["VHF", "UHF", "L", "S", "C", "X", "Ku", "K", "Ka", "Q", "V", "E", "optical"];

export const STATUS: Record<AppStatus, { label: string; tone: "neutral" | "accent" | "info" | "warn" | "ok" | "alarm" }> = {
  not_started: { label: "Not started", tone: "neutral" },
  preparing: { label: "Preparing", tone: "accent" },
  submitted: { label: "Submitted", tone: "info" },
  under_review: { label: "Under review", tone: "info" },
  info_requested: { label: "Information requested", tone: "warn" },
  granted: { label: "Granted", tone: "ok" },
  refused: { label: "Refused", tone: "alarm" },
  withdrawn: { label: "Withdrawn", tone: "neutral" },
};

/** Allowed next statuses — mirrors app/app/planner/tracker.py TRANSITIONS. */
export const NEXT_STATUS: Record<AppStatus, AppStatus[]> = {
  not_started: ["preparing", "submitted", "withdrawn"],
  preparing: ["submitted", "withdrawn"],
  submitted: ["under_review", "info_requested", "granted", "refused", "withdrawn"],
  under_review: ["info_requested", "granted", "refused", "withdrawn"],
  info_requested: ["under_review", "granted", "refused", "withdrawn"],
  granted: [],
  refused: ["preparing"],
  withdrawn: ["preparing"],
};

export const CATEGORY: Record<string, string> = {
  space_activity: "Space activity",
  itu_filing: "ITU filing",
  spectrum: "Spectrum",
  earth_station: "Earth station",
  market_access: "Market access",
  remote_sensing: "Remote sensing",
  launch: "Launch",
  registration: "Registration",
};

export const BASIS: Record<string, { label: string; hint: string; tone: "outline" | "neutral" | "dashed" }> = {
  statutory: { label: "Statutory", hint: "A time limit set in law", tone: "outline" },
  practice: { label: "Published practice", hint: "The authority's published guidance", tone: "neutral" },
  estimate: { label: "Estimate", hint: "No official figure; based on experience", tone: "dashed" },
};

export const RISK = {
  late: { label: "Late", tone: "alarm" },
  tight: { label: "Tight", tone: "warn" },
  ok: { label: "On track", tone: "ok" },
} as const;
