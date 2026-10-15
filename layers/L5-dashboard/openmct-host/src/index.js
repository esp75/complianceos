/**
 * Celestia operator dashboard — openmct host entry (ADR-0003, ADR-0015).
 *
 * Installs the vendored openmct (provided at runtime from `external/openmct/`, marked external
 * in the build) plus the Celestia compliance-status plugin. Runtime config (BFF URL, org, token)
 * comes from `window.CELESTIA` so the same bundle deploys against dev/prod without a rebuild.
 *
 * This is the first-slice host: it wires one plugin. Default openmct plugins, theming, and the
 * shared-session-cookie auth handshake (ADR-0003 open question) land with the deployment slice.
 */

import openmct from 'openmct';
import ComplianceStatusPlugin from '@celestia/openmct-compliance-status';

const config = globalThis.CELESTIA ?? {};

openmct.setAssetPath(config.openmctAssetPath ?? './node_modules/openmct/dist');

openmct.install(
  ComplianceStatusPlugin({
    baseUrl: config.baseUrl ?? '/api',
    orgId: config.orgId,
    token: () => config.token
  })
);

openmct.start();
