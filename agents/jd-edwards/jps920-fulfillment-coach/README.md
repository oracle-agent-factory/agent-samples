# JDE JPS920 Fulfillment Coach

End-user-oriented, read-only fulfillment coach configured for JDE environment `JPS920`, role `*ALL`, and device `paf-jde-agent`. Builder-managed connection settings stay out of the conversation while the coach learns business corrections incrementally across chat sessions.

## What this sample demonstrates

- Static connection context configured by the builder rather than requested from the end user.
- Implicit Agent Memory based on realistic, one-at-a-time corrections.
- Cross-session enforcement of prioritization, active-status, donor-reserve, and approval rules.
- A visible `Applied from your prior feedback` audit section when recalled feedback materially affects an analysis.
- Read-only recommendations with an explicit human approval boundary.

The included workflow was exported from Private Agent Factory 26.7.0.0.0 after live cross-session validation. The archive contains the workflow, not its learned memories or credentials.

## Prerequisites

- A compatible Oracle AI Database Private Agent Factory environment with Agent Memory enabled.
- Network access to a JD Edwards EnterpriseOne AIS server hosting the intended JPS920 environment.
- A JDE application user with Basic Auth and read access to F4211, F4201, F41021, F4311, F4101, and F0101.
- An LLM connection available to the imported agent.

The supplied OpenAPI definition fixes the environment, role, and device header values. Clone and rename the sample instead of allowing end users to change those values at runtime.

## Import and configure

1. Create a REST API source from [`assets/jde-fulfillment-openapi.json`](assets/jde-fulfillment-openapi.json), verify its AIS server URL, and configure JDE Basic Auth.
2. Import `jde-jps920-fulfillment-coach.paf` using the archive password supplied through the approved secret-sharing channel.
3. Rebind the REST API Tools node to the source created in step 1 and select an available model if necessary.
4. Enable Agent Memory and cross-thread sharing for the same user.
5. Confirm the agent name and description make the fixed JPS920/read-only scope clear, then run the demo from a clean memory state.

The workflow-only archive excludes model configuration, the REST data source, credentials, and all runtime memory records.

## Incremental-correction memory demo

### Session 1 — teach through normal feedback

1. `Can you review today's backorders and tell me what we should tackle first?`
2. After the initial recommendation: `We do not prioritize by quantity. Start with the earliest requested line that is still active.`
3. `Good. Make the status rule explicit: any line with last status 900 is inactive and stays out of the fulfillment queue.`
4. `For cross-branch recovery, do not recommend a donor if its indicative balance would fall below 1,000 units after the move. Show the arithmetic.`
5. `One more thing: anything that changes JDE needs my approval. Keep your recommendations read-only until then.`

Start a new chat with the same agent and user.

### Session 2 — apply the learned rules

1. `Can you review today's backorders and tell me what we should tackle first? If the local branch cannot cover it, include the best cross-branch fallback and show the numbers.`
2. `Assuming those checks pass, should the team release it?`

Expected behavior:

- The agent connects without asking for environment, role, device, or credentials.
- It prioritizes the earliest requested active line and excludes last-status-900 lines.
- It labels every donor that breaches the post-transfer 1,000-unit floor as ineligible and shows the arithmetic.
- The `Applied from your prior feedback` section lists only relevant recalled business rules and how they affected the result. It does not expose memory IDs, timestamps, confidence values, or connection settings.
- The follow-up requires explicit human approval and authorized execution; the agent does not claim to release anything.

Agent Memory retrieval is relevance-based. The audit section reports the prior feedback actually supplied to and applied by the agent in that turn; it does not claim that every stored memory was retrieved.

## Contents

- `jde-jps920-fulfillment-coach.paf` — CI-built password-protected Agent Builder release asset
- `workflow.json` — exact serialized workflow payload from the server export
- `archive-metadata.json` — server-generated export metadata
- [`assets/agent-instructions.md`](assets/agent-instructions.md) — readable copy of the custom instructions
- [`assets/jde-fulfillment-openapi.json`](assets/jde-fulfillment-openapi.json) — static JPS920 REST source definition
- `slides/` — reserved for presentation material; no deck is included

