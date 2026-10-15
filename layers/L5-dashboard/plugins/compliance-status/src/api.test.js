import { describe, expect, test } from 'bun:test';
import { ComplianceApiError, fetchComplianceStatus } from './api.js';

function stubFetch(response) {
  const calls = [];
  const fetchImpl = async (url, init) => {
    calls.push({ url, init });
    return response;
  };
  return { fetchImpl, calls };
}

describe('fetchComplianceStatus', () => {
  test('builds the URL and forwards the bearer token', async () => {
    const { fetchImpl, calls } = stubFetch({ ok: true, json: async () => ({ org_id: '01ORG' }) });
    const out = await fetchComplianceStatus({
      baseUrl: 'https://api.celestia.dynamics/',
      orgId: '01ORG',
      token: 'tok',
      fetchImpl
    });
    expect(out.org_id).toBe('01ORG');
    expect(calls[0].url).toBe('https://api.celestia.dynamics/compliance/status?org_id=01ORG');
    expect(calls[0].init.headers.Authorization).toBe('Bearer tok');
  });

  test('omits the auth header when no token', async () => {
    const { fetchImpl, calls } = stubFetch({ ok: true, json: async () => ({}) });
    await fetchComplianceStatus({ baseUrl: 'http://t', orgId: '01ORG', fetchImpl });
    expect(calls[0].init.headers.Authorization).toBeUndefined();
  });

  test('raises ComplianceApiError with status on non-2xx', async () => {
    const { fetchImpl } = stubFetch({ ok: false, status: 403, json: async () => ({}) });
    const err = await fetchComplianceStatus({ baseUrl: 'http://t', orgId: '01ORG', fetchImpl }).catch((e) => e);
    expect(err).toBeInstanceOf(ComplianceApiError);
    expect(err.status).toBe(403);
  });

  test('requires baseUrl and orgId', async () => {
    expect(fetchComplianceStatus({ orgId: 'x' })).rejects.toThrow('baseUrl is required');
    expect(fetchComplianceStatus({ baseUrl: 'http://t' })).rejects.toThrow('orgId is required');
  });
});
