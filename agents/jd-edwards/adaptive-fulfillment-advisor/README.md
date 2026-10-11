# JD Edwards Adaptive Fulfillment Advisor

Read-only JDE fulfillment advisor that learns connection details, operating constraints, and corrections through ordinary work conversations, then applies relevant context in later sessions.

## What this sample demonstrates

- Implicit use of Private Agent Factory Agent Memory: the end user does not issue memory-management commands.
- Natural setup when genuinely required connection context is missing.
- Incremental correction of prioritization, status, donor-reserve, and approval assumptions.
- Silent cross-session continuity in a later fulfillment review.

The included workflow was exported from Private Agent Factory 26.7.0.0.0 after live cross-session validation. Learned memory records are deliberately excluded from the sample.

## Prerequisites

- A compatible Oracle AI Database Private Agent Factory environment with Agent Memory enabled.
- Network access to a JD Edwards EnterpriseOne AIS server.
- A JDE application user with Basic Auth and read access to F4211, F4201, F41021, F4311, F4101, and F0101.
- An LLM connection available to the imported agent.

The supplied OpenAPI definition leaves the JDE environment, role, and device headers unconstrained. The agent obtains them from the current conversation or the user's relevant prior context.

## Import and configure

1. Create a REST API source from [`assets/jde-fulfillment-openapi.json`](assets/jde-fulfillment-openapi.json), set the correct AIS server URL, and configure JDE Basic Auth.
2. Import `jd-edwards-adaptive-fulfillment-advisor.paf` with the archive password supplied through the approved secret-sharing channel.
3. Rebind the REST API Tools node to the newly created source and select an available model if necessary.
4. Enable Agent Memory and cross-thread sharing for the same user.
5. Start with no pre-seeded memories, then run both sessions below.

The workflow-only archive excludes credentials, model configuration, REST source configuration, and user memory.

## Implicit-learning demo

### Session 1 — ordinary work and correction

1. User: `Can you check our backorders and tell me what we should tackle first?`
2. The agent should ask only for the missing JDE environment, role, and device identifier.
3. User: `Use JPS920 with the *ALL role and ops-fulfillment-demo as the device ID. Those are our normal connection settings for JDE orders, backorders, fulfillment, and inventory.`
4. After the initial analysis, user: `That is not how our team triages this. Start with the earliest requested line that is still active, not the largest-value order, and treat status 900 lines as inactive.`
5. User: `Also, never recommend cross-branch stock if the donor would fall below 1,000 units after the move. Show the arithmetic.`
6. User: `Anything that changes JDE needs my approval. Rework the recommendation and keep it read-only.`

Start a new chat with the same agent and user.

### Session 2 — silent continuity

`Can you review today's backorders, tell me what we should tackle first, and give me the best cross-branch backup if its local branch cannot cover it? Show me the numbers and keep it aligned with how our team operates.`

Expected behavior:

- The fresh session does not ask for connection values if relevant prior context is retrieved.
- Status-900 lines are excluded and the earliest requested active line is prioritized.
- Every proposed donor is tested against the remembered floor with explicit arithmetic.
- Anything that could change JDE still requires explicit approval and authorized execution.
- The response ends with `JDE changes made: none (read-only analysis).`

## Contents

- `jd-edwards-adaptive-fulfillment-advisor.paf` — CI-built password-protected Agent Builder release asset
- `workflow.json` — exact serialized workflow payload from the server export
- `archive-metadata.json` — server-generated export metadata
- [`assets/agent-instructions.md`](assets/agent-instructions.md) — readable copy of the custom instructions
- [`assets/jde-fulfillment-openapi.json`](assets/jde-fulfillment-openapi.json) — user-context REST source definition
- `slides/` — reserved for presentation material; no deck is included

