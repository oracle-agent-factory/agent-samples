# Private Agent Factory Agent Samples

This repository is a source-first catalog of documented agents for Oracle AI Database Private Agent Factory. Human-reviewable workflow sources and supporting assets live in Git; password-protected `.paf` archives are generated, verified, and published by GitHub Actions.

## Included samples

| Sample | Connection context | Agent Memory behavior |
| --- | --- | --- |
| [JD Edwards Fulfillment Exception Agent](jd-edwards-fulfillment-exception-agent/) | Builder-managed JPS920 headers | None; grounded read-only analysis |
| [JD Edwards Fulfillment Memory Agent](jd-edwards-fulfillment-memory-agent/) | Supplied through an explicit named profile | Explicit setup and cross-session recall |
| [JD Edwards Adaptive Fulfillment Advisor](jd-edwards-adaptive-fulfillment-advisor/) | Learned when first needed | Implicit learning through ordinary work and corrections |
| [JDE JPS920 Fulfillment Coach](jde-jps920-fulfillment-coach/) | Builder-managed JPS920 headers | Implicit incremental corrections with a user-facing audit section |

The samples form a progression from a stateless shortage investigation to a realistic, end-user-oriented Agent Memory demonstration. All six JDE tools are read-only Simple Table Query operations over F4211, F4201, F41021, F4311, F4101, and F0101.

## Source and release contract

Each sample folder contains:

| File | Purpose |
| --- | --- |
| `workflow.json` | Exact plaintext Agent Builder custom-flow payload extracted from the official export |
| `archive-metadata.json` | Server export metadata retained for compatible rebuilds |
| `sample.json` | Validated documentation and release manifest source |
| `README.md` | Contributor-oriented explanation and setup notes |
| `assets/agent-instructions.md` | Readable copy of the custom instructions |
| `assets/*.json` | Sanitized OpenAPI or other distributable dependencies |
| `slides/` | Optional presentation material |

`workflow.json` is not presented as Open Agent Spec. It is the product's serialized visual custom-flow payload. These JDE flows currently cannot be exported as portable Open Agent Spec because their REST API Tools nodes are implemented by the Agent Builder runtime.

Generated `.paf` files are ignored by Git and must never be committed. The release workflow packages every `workflow.json`, decrypts the new archive in memory, compares the recovered JSON and metadata with the source, and only then publishes it.

## What the PAF contains

The generated archives are complete workflow-only imports for Private Agent Factory 26.7. They include:

- the visual graph, agent instructions, node settings, and workflow identifiers;
- the original compatible archive metadata;
- exactly one custom flow per sample.

They intentionally exclude:

- JDE or other application credentials;
- REST API data-source definitions and environment-local source IDs;
- LLM connection mappings;
- Agent Memory configuration switches;
- learned user memory records;
- JDE sample data.

After import, create the documented REST source, configure authentication, rebind the REST API Tools node, select a model, and enable Agent Memory where the sample requires it. Imported workflows remain unpublished until reviewed.

## Repository layout

```text
agent-samples/
├── <agent-slug>/
│   ├── workflow.json
│   ├── archive-metadata.json
│   ├── sample.json
│   ├── README.md
│   ├── assets/
│   └── slides/
├── docs/                         # Generated catalog and per-agent Pages
├── scripts/
│   ├── build_release.py          # Build, decrypt, compare, checksum
│   ├── generate_docs.py          # Validate manifests and generate Pages
│   └── utilities/
│       └── agent_sample.py       # Extract, inspect, and package PAFs
├── tests/
└── .github/workflows/
    ├── pages.yml
    └── release.yml
```

## Set up locally

Python 3.10 or newer is required.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r scripts/requirements.txt
```

Passwords are prompted for securely by the archive utility. Automation reads the passphrase from a named environment variable. Never commit it, print it, place it in `sample.json`, or put it directly on a command line.

## Extract a UI export into reviewable source

Export one custom flow from **My Custom Flows**, then run:

```bash
python scripts/utilities/agent_sample.py create-from-paf ~/Downloads/exported_flows_*.paf
```

The command asks for the export passphrase, validates the envelope and ZIP, requires exactly one flow, and creates `workflow.json`, `archive-metadata.json`, and starter documentation directories. It does not copy the generated binary into the sample folder.

For non-interactive automation:

```bash
export PAF_PASSWORD_FROM_SECRET_STORE='...'
python scripts/utilities/agent_sample.py create-from-paf exported.paf \
  --password-env PAF_PASSWORD_FROM_SECRET_STORE
```

Add and complete `sample.json` in the new folder before committing it. The documentation build intentionally fails when required documentation is absent.

## Build and inspect archives

Build all release assets with the common repository archive passphrase:

```bash
export PAF_ARCHIVE_PASSWORD='...'
python scripts/build_release.py
```

The command writes only to ignored `dist/`:

```text
dist/
├── <agent-slug>.paf
├── manifest.json
├── SHA256SUMS
└── RELEASE_NOTES.md
```

To build a single sample:

```bash
python scripts/utilities/agent_sample.py pack <agent-folder> \
  --password-env PAF_ARCHIVE_PASSWORD
```

To validate and summarize a downloaded archive without exposing its graph or passphrase:

```bash
python scripts/utilities/agent_sample.py inspect path/to/agent.paf \
  --password-env PAF_ARCHIVE_PASSWORD
```

The PAF envelope uses PBKDF2-HMAC-SHA256 with 100,000 iterations, a random 16-byte salt, and a 32-byte key. AES-256-GCM uses a random 12-byte IV. The file stores Base64 of `salt || IV || ciphertext || tag`.

The common passphrase provides format-compatible archive protection and import gating, not source confidentiality: the workflow source is intentionally reviewable in this repository. Distribute the passphrase through an approved secret-sharing channel.

## GitHub Actions and releases

Set the repository Actions secret once:

```bash
gh secret set PAF_ARCHIVE_PASSWORD
```

The command prompts for the value. Use the repository-specific common archive passphrase, never an Oracle account password.

On every push to `main`, `.github/workflows/release.yml`:

1. runs all tests and validates the documentation manifests;
2. builds all encrypted archives;
3. decrypts and compares every generated archive with its source;
4. produces SHA-256 checksums and a machine-readable manifest;
5. uploads the complete `dist/` directory as a workflow artifact;
6. replaces the rolling prerelease tagged `latest`.

Pushing a `v*` tag publishes a permanent versioned release using the same validated assets. Release notes never contain the archive passphrase.

## GitHub Pages documentation

`sample.json` is the documentation contract. It records:

- title, summary, category, workflow version, and compatible PAF version;
- connection ownership and Agent Memory behavior;
- capabilities, prerequisites, tools, and safety controls;
- import and binding steps;
- realistic multi-session demo turns and expected outcomes;
- validation date, environment, status, and notes;
- source and release artifact names.

Generate the site locally:

```bash
python scripts/generate_docs.py \
  --repository-url https://github.com/oracle-agent-factory/agent-samples/tree/main \
  --release-base-url https://github.com/oracle-agent-factory/agent-samples/releases/download/latest
python -m http.server 8000 --directory docs
```

Open `http://localhost:8000`. The site includes a catalog, a detailed page for every agent, a tested chat flow, direct release downloads, source links, and `agents.json` for machine-readable discovery.

The Pages workflow regenerates and validates the site on every push to `main` and always uploads `rendered-agent-pages-<commit>` as an Actions artifact. Public repositories deploy automatically.

For a private repository, the organization plan must support GitHub Pages. Enable Pages with **Build and deployment → Source → GitHub Actions**, then create the repository variable `ENABLE_GITHUB_PAGES=true`. Until then, deployment is skipped without hiding documentation-build failures.

## Validate a contribution

```bash
python -m unittest discover -s tests -v
python scripts/generate_docs.py
PAF_ARCHIVE_PASSWORD='a-local-test-secret' python scripts/build_release.py
```

Before contributing, confirm that:

- the workflow imports into a compatible non-production Private Agent Factory environment;
- `sample.json` accurately documents prerequisites, tool scope, setup, demo turns, and validation;
- `workflow.json` remains the exact payload intended for packaging;
- environment-local dependencies can be rebound after import;
- memory-enabled samples exclude learned user data;
- OpenAPI and other assets are sanitized and redistribution-safe;
- no passwords, credentials, cookies, tokens, or customer-confidential data are present;
- no `.paf` file is tracked in Git.

## Format reference

The archive layout and password envelope follow the internal Agent Builder import/export specification. The repository utility packages an existing valid Agent Builder graph; it does not translate an arbitrary agent definition into a custom flow.
