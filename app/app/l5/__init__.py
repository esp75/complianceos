"""L5 dashboard backend helpers.

Pure, framework-agnostic logic that backs the operator dashboard's data endpoints.
The openmct plugins (``layers/L5-dashboard/``) read these through the BFF; keeping the
rollup here (not in the router or the browser) makes it unit-testable and keeps the
tenancy join server-side (ADR-0015)."""
