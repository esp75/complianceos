/**
 * Compliance Status openmct plugin (ADR-0015).
 *
 * Registers a Celestia object type + a view provider that mounts the Vue panel. The panel's
 * data comes from the BFF rollup (`fetchComplianceStatus`); the rollup→view-model mapping is
 * `toViewModel`. openmct itself is provided by the host at runtime (peer dependency / external
 * in the build) — never imported here, only received as `install(openmct)`.
 *
 * @param {object} options
 * @param {string} options.baseUrl - BFF base URL.
 * @param {string} options.orgId   - organization ULID to show.
 * @param {() => (string|undefined)} [options.token] - returns the current bearer token.
 */

import { createApp } from 'vue';
import { fetchComplianceStatus } from './api.js';
import ComplianceStatusPanel from './component.js';
import { toViewModel } from './transform.js';

export const TYPE_KEY = 'celestia.compliance-status';
export const VIEW_KEY = 'celestia.compliance-status.view';

export default function ComplianceStatusPlugin(options = {}) {
  const { baseUrl, orgId, token } = options;

  return function install(openmct) {
    openmct.types.addType(TYPE_KEY, {
      name: 'Compliance Status',
      description: 'Per-Framework, per-Control compliance status for an organization.',
      cssClass: 'icon-list-view',
      creatable: false
    });

    openmct.objectViews.addProvider({
      key: VIEW_KEY,
      name: 'Compliance Status',
      cssClass: 'icon-list-view',
      canView: (domainObject) => domainObject.type === TYPE_KEY,
      view: (domainObject) => {
        let app = null;
        const props = { model: null, error: null };

        async function load() {
          try {
            const payload = await fetchComplianceStatus({
              baseUrl,
              orgId: domainObject.orgId ?? orgId,
              token: typeof token === 'function' ? token() : token
            });
            props.model = toViewModel(payload);
          } catch (err) {
            props.error = String(err?.message ?? err);
          }
        }

        return {
          async show(element) {
            await load();
            app = createApp(ComplianceStatusPanel, props);
            app.mount(element);
          },
          destroy() {
            if (app) {
              app.unmount();
              app = null;
            }
          }
        };
      }
    });
  };
}
