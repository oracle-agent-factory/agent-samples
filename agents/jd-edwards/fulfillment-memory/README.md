# JD Edwards Fulfillment Memory Agent

Read-only JDE fulfillment analysis that carries a user-specific execution context and recovery policy across chat sessions with Private Agent Factory Agent Memory.

## What this sample demonstrates

- Cross-session recall of JDE environment, role, and device values that are intentionally not hardcoded in the REST source.
- Recall and enforcement of a user-defined recovery policy.
- Numeric eligibility checks, including post-transfer donor-cushion arithmetic.
- A read-only approval boundary for any action that could change JDE.

This variant is intentionally explicit about establishing and recalling a named operating profile. For a more natural correction-driven experience, use the Adaptive Fulfillment Advisor or JPS920 Fulfillment Coach samples.

The included workflow was exported from Private Agent Factory 26.7.0.0.0 after a live two-session validation. Learned memory records are user-specific runtime data and are not part of the export.

## Prerequisites

- A compatible Oracle AI Database Private Agent Factory environment with Agent Memory enabled.
- Network access to a JD Edwards EnterpriseOne AIS server.
- A JDE application user with Basic Auth and read access to F4211, F4201, F41021, F4311, F4101, and F0101.
- An LLM connection available to the imported agent.

The supplied OpenAPI definition requires the agent to supply environment, role, and device headers at runtime. It has no constants, defaults, or enums for those three values.

## Import and configure

1. Create a REST API source from [`assets/jde-fulfillment-openapi.json`](assets/jde-fulfillment-openapi.json), update its AIS server URL if needed, and configure JDE Basic Auth.
2. Import `jd-edwards-fulfillment-memory-agent.paf` using the archive password supplied through the approved secret-sharing channel.
3. Rebind the REST API Tools node to the newly created source. Source IDs are local to each Agent Factory environment.
4. Select an available model if necessary.
5. Enable Agent Memory for the imported agent and enable sharing across chat threads for the same user.
6. Run the two-session demo below before publishing.

The workflow-only archive excludes credentials, model configuration, the REST source, and all user memory records.

## Two-session memory demo

### Session 1 — establish the operating profile

1. `Hi, I'm taking over the North America fulfillment review. Let's call this the North America Fulfillment Standard. For this JDE connection, use environment JPS920, role *ALL, and device ops-fulfillment-demo. Please remember that for future chats. I'm only setting up today, so don't query JDE yet.`
2. `One more rule for that standard: a cross-branch candidate is eligible only when it addresses the earliest requested active line and leaves at least 1,000 units of indicative available balance in the donor branch after the proposed allocation. Anything that could change JDE needs explicit human approval. Please remember that too.`

Start a new chat with the same agent and user.

### Session 2 — recall and apply it

1. `Morning. Which JDE environment is saved in my North America Fulfillment Standard? Answer from memory only; do not query JDE.`
2. `What role and device identifier are saved for that same standard? Answer from memory only; do not query JDE.`
3. `Before we look at today's orders, remind me of the saved cross-branch eligibility rule and the approval control for that standard. Please do not query JDE yet.`
4. `Great—use that remembered standard to run today's fulfillment exception review. Find up to five backordered sales-order lines, determine which order deserves investigation first, and recommend the single best eligible cross-branch recovery action. Show the post-allocation cushion arithmetic and do not change JDE.`

During the original validation, the fresh session recalled all connection values and policy constraints, rejected donors that would fall below the 1,000-unit floor, and made no JDE changes. Exact orders and balances will differ by environment.

## Contents

- `jd-edwards-fulfillment-memory-agent.paf` — CI-built password-protected Agent Builder release asset
- `workflow.json` — exact serialized workflow payload from the server export
- `archive-metadata.json` — server-generated export metadata
- [`assets/agent-instructions.md`](assets/agent-instructions.md) — readable copy of the custom instructions
- [`assets/jde-fulfillment-openapi.json`](assets/jde-fulfillment-openapi.json) — user-context REST source definition
- `slides/` — reserved for presentation material; no deck is included

