import { describe, expect, test } from 'bun:test';
import { STATUS, statusColor, statusLabel, summaryLine, toViewModel } from './transform.js';

const PAYLOAD = {
  org_id: '01ORG',
  summary: { compliant: 1, partial: 1, not_assessed: 1, total: 3, percentCompliant: 33.3 },
  frameworks: [
    {
      shortName: 'ISO-24113',
      framework: '2023',
      controlCount: 2,
      summary: { compliant: 1, partial: 1, not_assessed: 0 },
      percentCompliant: 50.0,
      controls: [
        { refCode: 'ISO 24113 §6.4', title: 'Collision avoidance', status: 'compliant', evidenceCount: 2, evidence: [{ id: 'E1' }] },
        { refCode: 'ISO 24113 §6.2', title: 'Disposal', status: 'partial', evidenceCount: 1, evidence: [] }
      ]
    }
  ]
};

describe('toViewModel', () => {
  test('maps org, summary and frameworks', () => {
    const vm = toViewModel(PAYLOAD);
    expect(vm.orgId).toBe('01ORG');
    expect(vm.percentCompliant).toBe(33.3);
    expect(vm.frameworks).toHaveLength(1);
    expect(vm.frameworks[0].shortName).toBe('ISO-24113');
  });

  test('decorates each control with a label and color', () => {
    const vm = toViewModel(PAYLOAD);
    const [c0, c1] = vm.frameworks[0].controls;
    expect(c0.label).toBe('Compliant');
    expect(c0.color).toBe(statusColor(STATUS.COMPLIANT));
    expect(c1.label).toBe('Partial');
    expect(c1.evidenceCount).toBe(1);
  });

  test('tolerates an empty payload', () => {
    const vm = toViewModel({});
    expect(vm.frameworks).toEqual([]);
    expect(vm.orgId).toBeNull();
  });
});

describe('summaryLine', () => {
  test('formats the org rollup', () => {
    expect(summaryLine(PAYLOAD.summary)).toBe('1/3 compliant · 1 partial · 1 not assessed (33.3%)');
  });

  test('derives total when absent', () => {
    expect(summaryLine({ compliant: 2, partial: 0, not_assessed: 1 })).toContain('2/3 compliant');
  });
});

describe('status presentation', () => {
  test('known statuses have labels and colors', () => {
    expect(statusLabel(STATUS.NOT_ASSESSED)).toBe('Not assessed');
    expect(statusColor(STATUS.PARTIAL)).toMatch(/^#/);
  });

  test('unknown status falls back to not-assessed color', () => {
    expect(statusColor('weird')).toBe(statusColor(STATUS.NOT_ASSESSED));
  });
});
