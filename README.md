# Private Agent Factory Agent Samples

This repository is a catalog of self-contained agents that can be imported into
Oracle AI Database Private Agent Factory. Each top-level agent folder contains
the importable `.paf` archive, its Agent Builder flow specification,
documentation, presentation material, and supporting assets.

## Repository layout

```text
agent-samples/
├── <agent-name>/
│   ├── <agent-name>.paf
│   ├── agent-spec.json
│   ├── archive-metadata.json
│   ├── README.md
│   ├── slides/
│   └── assets/
├── docs/                       # Generated GitHub Pages catalog
├── scripts/
│   ├── generate_docs.py
│   └── utilities/
│       └── agent_sample.py
└── .github/workflows/pages.yml
```

For this repository, `agent-spec.json` is the serialized Agent Builder custom
flow stored in the archive under `flows/*.json`. It is also the source of the
agent name, description, category, and version shown in the generated catalog.

## Set up the utilities

Python 3.10 or newer is required. The archive utility additionally uses the
`cryptography` package.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r scripts/requirements.txt
```

Passwords are prompted for securely by default. For automation, place the
password in an environment variable and identify that variable with
`--password-env`. Never commit a password or put one directly on a command
line.

## Add an agent exported from the UI

Export a single custom flow from **My Custom Flows** in Private Agent Factory,
then run:

```bash
python scripts/utilities/agent_sample.py create-from-paf ~/Downloads/exported_flows_*.paf
```

The utility decrypts and validates the archive, requires it to contain exactly
one flow, and creates a top-level folder named from the flow. It retains the
original `.paf`, writes the flow to `agent-spec.json`, preserves the export
metadata, and creates starter README, slides, and assets directories.

For non-interactive use:

```bash
export PAF_PASSWORD='use-a-secret-store-in-real-automation'
python scripts/utilities/agent_sample.py create-from-paf exported.paf \
  --password-env PAF_PASSWORD
```

## Create an importable `.paf` programmatically

Start with a complete `agent-spec.json` containing the fields produced by an
Agent Builder export: `name`, `description`, `category`, `icon`, `published`,
`flowGraph`, and `data`. Then run:

```bash
python scripts/utilities/agent_sample.py create-from-spec path/to/agent-spec.json \
  --application-version 26.4.0.0.0
```

This creates the agent folder and a password-protected `.paf`. To rebuild the
archive after editing an existing sample:

```bash
python scripts/utilities/agent_sample.py pack <agent-folder>
```

The archive format follows the Agent Builder import/export specification:

```text
metadata.json
flows/
  <agent_id>_<sanitized_name>.json
```

The ZIP bytes are protected using PBKDF2-HMAC-SHA256 with 100,000 iterations,
a random 16-byte salt, and a 32-byte key; AES-256-GCM uses a random 12-byte IV.
The `.paf` stores Base64 of `salt || IV || ciphertext || 16-byte tag`.

Important: the utility packages a flow payload; it does not translate an
arbitrary agent definition into a valid Agent Builder graph. The `data` and
`flowGraph` content must already be valid for the target Private Agent Factory
release. Always test the generated archive in a non-production environment.

## Inspect an archive

```bash
python scripts/utilities/agent_sample.py inspect path/to/agent.paf
```

The command validates authentication, ZIP integrity, metadata, and flow JSON,
then prints only summary information. It does not print the flow graph or the
password.

## Generate the documentation site

```bash
python scripts/generate_docs.py
python -m http.server 8000 --directory docs
```

Open `http://localhost:8000`. The generator discovers top-level folders that
contain `agent-spec.json` and builds the catalog from their descriptions.

The GitHub Actions workflow regenerates the catalog and publishes `docs/` to
GitHub Pages on every push to `main`. In the GitHub repository settings, set
**Pages → Build and deployment → Source** to **GitHub Actions** once.

## Validate changes

```bash
python -m unittest discover -s tests -v
python scripts/generate_docs.py
```

Before contributing an agent, verify that:

- the `.paf` imports into a compatible Private Agent Factory test environment;
- `agent-spec.json` has an accurate, useful description;
- the README lists prerequisites and example prompts;
- no passwords, credentials, tokens, or environment secrets are committed;
- slides and other assets do not contain customer-confidential information.

## Source specification

The archive structure and password-protection behavior are based on the
internal [Agent Builder - Import / Export specification](https://confluence.oraclecorp.com/confluence/pages/viewpage.action?pageId=19943727175),
including its password-based archive protection section.
