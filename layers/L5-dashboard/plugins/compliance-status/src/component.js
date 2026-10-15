/**
 * Vue 3 component for the Compliance Status panel.
 *
 * Authored with a render function (no SFC template) so it bundles without the Vue SFC
 * compiler — keeps the headless `bun build` light (ADR-0015). Mission-control idiom per
 * DESIGN.md: dark background, monospace refCodes, square corners, status as a color chip.
 */

import { defineComponent, h } from 'vue';
import { statusColor } from './transform.js';

const styles = {
  root: { background: '#0B0E14', color: '#E5E7EB', font: '14px Inter, system-ui, sans-serif', padding: '12px' },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '8px' },
  summary: { font: '12px "JetBrains Mono", monospace', color: '#9CA3AF' },
  fwTitle: { margin: '12px 0 4px', fontWeight: '600' },
  row: { display: 'flex', alignItems: 'center', gap: '8px', padding: '4px 0', borderBottom: '1px solid #1F2937' },
  chip: { width: '8px', height: '8px', borderRadius: '2px', flex: '0 0 auto' },
  ref: { font: '12px "JetBrains Mono", monospace', color: '#9CA3AF', flex: '0 0 160px' },
  title: { flex: '1 1 auto' },
  count: { font: '12px "JetBrains Mono", monospace', color: '#6B7280' },
  empty: { color: '#6B7280', padding: '8px 0' },
  error: { color: '#EF4444', padding: '8px 0' }
};

function controlRow(control) {
  return h('div', { style: styles.row }, [
    h('span', { style: { ...styles.chip, background: statusColor(control.status) }, title: control.label }),
    h('span', { style: styles.ref }, control.refCode),
    h('span', { style: styles.title }, control.title),
    h('span', { style: styles.count }, `${control.label} · ${control.evidenceCount} ev`)
  ]);
}

function frameworkBlock(framework) {
  return h('section', {}, [
    h('div', { style: styles.fwTitle }, `${framework.shortName} (${framework.percentCompliant}% compliant)`),
    ...framework.controls.map(controlRow)
  ]);
}

export default defineComponent({
  name: 'ComplianceStatusPanel',
  props: {
    model: { type: Object, default: null },
    error: { type: String, default: null }
  },
  render() {
    if (this.error) {
      return h('div', { style: { ...styles.root, ...styles.error } }, `Failed to load compliance status: ${this.error}`);
    }
    if (!this.model) {
      return h('div', { style: { ...styles.root, ...styles.empty } }, 'Loading compliance status…');
    }
    if (!this.model.frameworks.length) {
      return h('div', { style: { ...styles.root, ...styles.empty } }, 'No frameworks loaded.');
    }
    return h('div', { style: styles.root }, [
      h('div', { style: styles.header }, [
        h('strong', {}, 'Compliance Status'),
        h('span', { style: styles.summary }, this.model.summaryLine)
      ]),
      ...this.model.frameworks.map(frameworkBlock)
    ]);
  }
});
