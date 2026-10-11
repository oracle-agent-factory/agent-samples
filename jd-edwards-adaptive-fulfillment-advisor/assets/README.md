# Supporting assets

- `agent-instructions.md` is a readable copy of the custom instruction embedded in `workflow.json`.
- `jde-fulfillment-openapi.json` defines six read-only JD Edwards EnterpriseOne Simple Table Query operations for F4211, F4201, F41021, F4311, F4101, and F0101.

The JDE environment, role, and device headers are required but deliberately have no default, constant, or enum. The agent must obtain them from the current user context. The server URL is an example deployment endpoint and may need to be changed before import.

The file declares Basic Auth but contains no username, password, token, cookie, or other credential. Configure authentication in Private Agent Factory after creating the REST API data source.

