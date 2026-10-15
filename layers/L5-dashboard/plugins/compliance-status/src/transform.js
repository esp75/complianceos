/**
 * Pure view-model + presentation mapping for the Compliance Status panel.
 *
 * Framework-free on purpose (ADR-0015): the BFF owns the Standards×Evidence join and
 * ships the rolled-up payload from `GET /compliance/status`; this turns that payload into
 * something the Vue view renders, and is unit-tested headlessly with no openmct/Vue.
 */

export const STATUS = Object.freeze({
  COMPLIANT: 'compliant',
  PARTIAL: 'partial',
  NOT_ASSESSED: 'not_assessed'
});

export const STATUS_LABELS = Object.freeze({
  [STATUS.COMPLIANT]: 'Compliant',
  [STATUS.PARTIAL]: 'Partial',
  [STATUS.NOT_ASSESSED]: 'Not assessed'
});

// Operator-mode status colors. Green/amber/grey for the three tiers; the DESIGN.md
// `--alarm` red (#EF4444) is reserved for conjunction / hard non-compliance, not the
// "not assessed" resting state.
export const STATUS_COLORS = Object.freeze({
  [STATUS.COMPLIANT]: '#22C55E',
  [STATUS.PARTIAL]: '#F59E0B',
  [STATUS.NOT_ASSESSED]: '#6B7280'
});

export function statusLabel(status) {
  return STATUS_LABELS[status] ?? status;
}

export function statusColor(status) {
  return STATUS_COLORS[status] ?? STATUS_COLORS[STATUS.NOT_ASSESSED];
}

function toControl(control) {
  return {
    refCode: control.refCode,
    title: control.title,
    status: control.status,
    label: statusLabel(control.status),
    color: statusColor(control.status),
    evidenceCount: control.evidenceCount ?? 0,
    evidence: control.evidence ?? []
  };
}

function toFramework(framework) {
  return {
    shortName: framework.shortName,
    framework: framework.framework,
    controlCount: framework.controlCount ?? (framework.controls ?? []).length,
    summary: framework.summary ?? {},
    percentCompliant: framework.percentCompliant ?? 0,
    controls: (framework.controls ?? []).map(toControl)
  };
}

/**
 * Build the panel view-model from a `/compliance/status` payload.
 * @param {object} payload - `{ org_id, frameworks: [...], summary: {...} }`
 */
export function toViewModel(payload) {
  const summary = payload?.summary ?? {};
  const frameworks = (payload?.frameworks ?? []).map(toFramework);
  return {
    orgId: payload?.org_id ?? null,
    percentCompliant: summary.percentCompliant ?? 0,
    summary,
    summaryLine: summaryLine(summary),
    frameworks
  };
}

/** One-line org rollup, e.g. "1/3 compliant · 1 partial · 1 not assessed (33.3%)". */
export function summaryLine(summary) {
  const compliant = summary[STATUS.COMPLIANT] ?? 0;
  const partial = summary[STATUS.PARTIAL] ?? 0;
  const notAssessed = summary[STATUS.NOT_ASSESSED] ?? 0;
  const total = summary.total ?? compliant + partial + notAssessed;
  const pct = summary.percentCompliant ?? 0;
  return `${compliant}/${total} compliant · ${partial} partial · ${notAssessed} not assessed (${pct}%)`;
}
