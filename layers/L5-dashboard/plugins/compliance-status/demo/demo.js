/**
 * Standalone preview of the Compliance Status panel (dev-only, not shipped).
 *
 * Mounts the real Vue component through the real `toViewModel` transform with a representative
 * `/compliance/status` payload, so the panel can be eyeballed without openmct, the BFF, or auth.
 * The live dashboard wires the same component to the BFF via `plugin.js` (ADR-0015).
 */

import { createApp } from 'vue';
import ComplianceStatusPanel from '../src/component.js';
import { toViewModel } from '../src/transform.js';

// Representative rollup payload — the three Phase-1 frameworks with mixed status.
const SAMPLE = {
  org_id: '01ORGDEMO',
  summary: { compliant: 4, partial: 2, not_assessed: 7, total: 13, percentCompliant: 30.8 },
  frameworks: [
    {
      shortName: 'ISO-24113',
      framework: '2023',
      percentCompliant: 50.0,
      summary: { compliant: 2, partial: 1, not_assessed: 1 },
      controls: [
        { refCode: 'ISO 24113 §6.1', title: 'General requirements', status: 'compliant', evidenceCount: 1 },
        { refCode: 'ISO 24113 §6.2', title: 'Post-mission disposal', status: 'compliant', evidenceCount: 2 },
        { refCode: 'ISO 24113 §6.3', title: 'Passivation of stored energy', status: 'partial', evidenceCount: 1 },
        { refCode: 'ISO 24113 §6.4', title: 'Prevention of on-orbit collisions', status: 'not_assessed', evidenceCount: 0 }
      ]
    },
    {
      shortName: 'EU-SA',
      framework: 'v1',
      percentCompliant: 40.0,
      summary: { compliant: 2, partial: 0, not_assessed: 3 },
      controls: [
        { refCode: 'EU-SA Art.1', title: 'Subject matter and scope', status: 'compliant', evidenceCount: 1 },
        { refCode: 'EU-SA Art.2', title: 'Definitions', status: 'not_assessed', evidenceCount: 0 },
        { refCode: 'EU-SA Art.3', title: 'Authorisation requirement', status: 'compliant', evidenceCount: 1 },
        { refCode: 'EU-SA Art.4', title: 'Risk assessment', status: 'not_assessed', evidenceCount: 0 },
        { refCode: 'EU-SA Art.5', title: 'Collision avoidance', status: 'not_assessed', evidenceCount: 0 }
      ]
    },
    {
      shortName: 'ITU-RR',
      framework: '2020',
      percentCompliant: 0.0,
      summary: { compliant: 0, partial: 1, not_assessed: 3 },
      controls: [
        { refCode: 'ITU-RR Art.11', title: 'Notification and recording of frequency assignments', status: 'partial', evidenceCount: 1 },
        { refCode: 'ITU-RR Art.21', title: 'Terrestrial and space services sharing', status: 'not_assessed', evidenceCount: 0 },
        { refCode: 'ITU-RR Art.22', title: 'Space services protection', status: 'not_assessed', evidenceCount: 0 },
        { refCode: 'ITU-RR Res.32', title: 'Bringing into use of frequency assignments', status: 'not_assessed', evidenceCount: 0 }
      ]
    }
  ]
};

createApp(ComplianceStatusPanel, { model: toViewModel(SAMPLE), error: null }).mount('#app');
