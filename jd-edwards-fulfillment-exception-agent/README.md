# JD Edwards Fulfillment Exception Agent

Read-only fulfillment exception analysis for JD Edwards EnterpriseOne. The agent uses live sales-order, inventory, inbound-supply, item, and address-book evidence to recommend an approval-ready recovery plan without changing JDE.

## What this sample demonstrates

- Grounded investigation of sales-order backorders through six bounded JDE Simple Table Query tools.
- Cross-checking line and header status before recommending recovery.
- Branch inventory and credible inbound purchase-order analysis.
- Explicit separation between evidence, recommendations, verification, and execution.
- A hard read-only control: the agent ends live analyses with `JDE changes made: none (read-only analysis).`

The included workflow was exported from Private Agent Factory 26.7.0.0.0 after live validation against the JPS920 sample environment. Results depend on the data and permissions in the target JDE environment.

## Prerequisites

- A compatible Oracle AI Database Private Agent Factory environment.
- Network access from Private Agent Factory to a JD Edwards EnterpriseOne AIS server.
- A JDE application user allowed to query the required tables through AIS. Configure the credentials as Basic Auth in the REST API data source; never place credentials in this repository or the OpenAPI file.
- Read access to F4211, F4201, F41021, F4311, F4101, and F0101.
- An LLM connection available to the imported agent.

The supplied OpenAPI definition is configured for environment `JPS920`, role `*ALL`, and device identifier `paf-jde-agent`. Review those non-secret execution-context values before using the sample elsewhere.

## Import and configure

1. In **Data Sources**, create a REST API source from [`assets/jde-fulfillment-openapi.json`](assets/jde-fulfillment-openapi.json). Update its `servers` URL if the target AIS endpoint differs.
2. Configure the new source with JDE Basic Auth and test one bounded endpoint call.
3. In **My Custom Flows**, import `jd-edwards-fulfillment-exception-agent.paf` and enter the archive password supplied through the approved secret-sharing channel.
4. Open the imported flow. Rebind its REST API Tools node to the source created in step 1; source IDs are environment-local and the export intentionally does not include REST source configuration.
5. Select an available model if the imported agent step is not already mapped to one in the target environment.
6. Test the prompts below, inspect every tool call, and publish only after the target results are correct.

Imported workflows are created unpublished. The `.paf` is a workflow-only export: it contains no JDE credentials, model configuration, REST API source, or learned user memory.

## Demo flow

1. `Find up to five sales order lines with backordered quantity and explain which one is the best recovery candidate.`
2. `Investigate sales order <number>. Show the exact line evidence, inventory by branch, credible inbound supply, and rank recovery options.`
3. `For item <item>, compare indicative availability across branches and identify relevant open inbound purchase-order lines. Do not make any JDE changes.`

Expected behavior:

- Queries are bounded to 50 rows or fewer unless the user asks for more.
- The agent uses fully qualified JDE field names and does not invent business data.
- Calculated inventory is called an indicative available balance unless the evidence is sufficient to label it ATP.
- Recommendations state what a human must verify or approve before execution.
- No write-back endpoint exists in the supplied data source.

## Contents

- `jd-edwards-fulfillment-exception-agent.paf` — CI-built password-protected Agent Builder release asset
- `workflow.json` — exact serialized workflow payload from the server export
- `archive-metadata.json` — server-generated export metadata
- [`assets/agent-instructions.md`](assets/agent-instructions.md) — readable copy of the custom instructions
- [`assets/jde-fulfillment-openapi.json`](assets/jde-fulfillment-openapi.json) — sanitized read-only REST data-source definition
- `slides/` — reserved for presentation material; no deck is included

