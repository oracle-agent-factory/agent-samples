# Supporting assets

- `agent-instructions.md` is a readable copy of the custom instruction embedded in `workflow.json`.
- `jde-fulfillment-openapi.json` defines six read-only JD Edwards EnterpriseOne Simple Table Query operations for F4211, F4201, F41021, F4311, F4101, and F0101.

The OpenAPI definition sets the JDE execution headers to environment `JPS920`, role `*ALL`, and device `paf-jde-agent`. Its server URL is an example deployment endpoint and may need to be changed before import.

The file declares Basic Auth but contains no username, password, token, cookie, or other credential. Configure authentication in Private Agent Factory after creating the REST API data source.

