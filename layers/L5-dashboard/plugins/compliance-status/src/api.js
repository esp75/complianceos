/**
 * Data adapter for the Compliance Status panel.
 *
 * Thin typed wrapper over the BFF's `GET /compliance/status?org_id=` (ADR-0015). The plugin
 * never builds URLs or parses responses inline — it calls this. `fetchImpl` is injectable so
 * the adapter is unit-testable headlessly without a browser or a live BFF.
 */

export class ComplianceApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = 'ComplianceApiError';
    this.status = status;
  }
}

/**
 * Fetch the compliance-status rollup for one organization.
 * @param {object} opts
 * @param {string} opts.baseUrl - BFF base URL, e.g. "https://api.celestia.dynamics".
 * @param {string} opts.orgId   - organization ULID.
 * @param {string} [opts.token] - bearer token forwarded to the BFF.
 * @param {typeof fetch} [opts.fetchImpl] - injectable fetch (defaults to global fetch).
 * @returns {Promise<object>} the raw `/compliance/status` payload.
 */
export async function fetchComplianceStatus({ baseUrl, orgId, token, fetchImpl }) {
  if (!baseUrl) {
    throw new ComplianceApiError('baseUrl is required');
  }
  if (!orgId) {
    throw new ComplianceApiError('orgId is required');
  }
  const doFetch = fetchImpl ?? globalThis.fetch;
  const url = `${baseUrl.replace(/\/$/, '')}/compliance/status?org_id=${encodeURIComponent(orgId)}`;
  const headers = token ? { Authorization: `Bearer ${token}` } : {};

  let resp;
  try {
    resp = await doFetch(url, { headers });
  } catch (cause) {
    throw new ComplianceApiError(`compliance-status request failed: ${cause}`);
  }
  if (!resp.ok) {
    throw new ComplianceApiError(`compliance-status returned ${resp.status}`, resp.status);
  }
  return resp.json();
}
