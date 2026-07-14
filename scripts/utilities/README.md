# Agent sample utility

`agent_sample.py` supports both repository onboarding paths:

- `create-from-paf` creates a sample folder from a single-flow archive exported
  by the Private Agent Factory UI.
- `create-from-spec` creates a sample folder and encrypted archive from a
  complete serialized Agent Builder flow.
- `pack` rebuilds the archive for an existing sample.
- `inspect` authenticates and validates an archive without exposing its graph.

Run `python scripts/utilities/agent_sample.py --help` or append `--help` to a
subcommand for the full option list.

The implementation follows the internal
[Agent Builder - Import / Export specification](https://confluence.oraclecorp.com/confluence/pages/viewpage.action?pageId=19943727175).
It uses a random 16-byte salt, PBKDF2-HMAC-SHA256 with 100,000 iterations, a
32-byte key, and AES-256-GCM with a random 12-byte IV. The Base64 envelope is
`salt || IV || ciphertext || 16-byte authentication tag`.

Programmatically generated metadata uses the documented application version,
export timestamp, included resource types, and resource counts. When a folder
originates from a real UI export, `archive-metadata.json` retains the exact
server-generated metadata so subsequent `pack` operations preserve it.

