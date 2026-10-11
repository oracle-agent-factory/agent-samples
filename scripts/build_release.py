#!/usr/bin/env python3
"""Build, round-trip validate, and inventory encrypted PAF release archives."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.utilities.agent_sample import (  # noqa: E402
    PafError,
    build_paf_bytes,
    decrypt_paf_bytes,
    parse_zip_bytes,
    slugify,
    validate_flow,
)


def _json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PafError(f"{path}: cannot read valid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise PafError(f"{path}: expected a JSON object")
    return value


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_release(root: Path, output: Path, password: str) -> dict[str, Any]:
    if not password:
        raise PafError("PAF archive password cannot be empty")
    root, output = root.resolve(), output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    for old in (*output.glob("*.paf"), output / "manifest.json", output / "SHA256SUMS", output / "RELEASE_NOTES.md"):
        if old.is_file():
            old.unlink()

    entries: list[dict[str, Any]] = []
    agents_root = root / "agents"
    folders = sorted(
        use_case
        for application in agents_root.iterdir()
        if application.is_dir() and not application.name.startswith(".")
        for use_case in application.iterdir()
        if use_case.is_dir()
        and not use_case.name.startswith(".")
        and (use_case / "sample.json").is_file()
    ) if agents_root.is_dir() else []
    if not folders:
        raise PafError(f"no sample.json manifests were found under {agents_root}")

    for folder in folders:
        sample = _json(folder / "sample.json")
        slug = sample.get("slug")
        if not isinstance(slug, str) or not slug or slugify(slug) != slug:
            raise PafError(f"{folder}/sample.json: slug must be a lowercase filename slug")
        application = sample.get("application")
        use_case = sample.get("useCase")
        if not isinstance(application, dict) or not isinstance(use_case, dict):
            raise PafError(f"{folder}/sample.json: application and useCase must be objects")
        if application.get("slug") != folder.parent.name:
            raise PafError(f"{folder}/sample.json: application.slug must match {folder.parent.name}")
        if use_case.get("slug") != folder.name:
            raise PafError(f"{folder}/sample.json: useCase.slug must match {folder.name}")
        if not all(
            isinstance(value, str) and value.strip()
            for value in (application.get("name"), use_case.get("name"))
        ):
            raise PafError(f"{folder}/sample.json: application.name and useCase.name are required")
        artifacts = sample.get("artifacts")
        if not isinstance(artifacts, dict):
            raise PafError(f"{folder}/sample.json: artifacts must be an object")
        workflow_name = artifacts.get("workflow")
        metadata_name = artifacts.get("archiveMetadata")
        release_asset = artifacts.get("releaseAsset")
        if workflow_name != "workflow.json" or metadata_name != "archive-metadata.json":
            raise PafError(f"{folder}/sample.json: canonical workflow or metadata path is invalid")
        if release_asset != f"{slug}.paf":
            raise PafError(f"{folder}/sample.json: release asset must be {slug}.paf")

        flow = validate_flow(_json(folder / workflow_name), str(folder / workflow_name))
        metadata = _json(folder / metadata_name)
        payload, used_metadata = build_paf_bytes([flow], password, metadata=metadata)
        archive = parse_zip_bytes(decrypt_paf_bytes(payload, password))
        if archive.metadata != used_metadata or len(archive.flows) != 1 or archive.flows[0][1] != flow:
            raise PafError(f"{slug}: encrypted archive failed exact round-trip validation")

        destination = output / release_asset
        destination.write_bytes(payload)
        digest = hashlib.sha256(payload).hexdigest()
        entries.append({
            "slug": slug,
            "application": {
                "slug": application["slug"],
                "name": application["name"].strip(),
            },
            "useCase": {
                "slug": use_case["slug"],
                "name": use_case["name"].strip(),
            },
            "sourcePath": f"agents/{application['slug']}/{use_case['slug']}",
            "name": flow["name"],
            "workflowId": flow.get("workflowId"),
            "workflowVersion": flow.get("version"),
            "applicationVersion": metadata.get("applicationVersion"),
            "asset": release_asset,
            "bytes": len(payload),
            "sha256": digest,
            "scope": "workflow-only",
        })

    manifest = {
        "schemaVersion": "1.0",
        "generatedAt": _utc_now(),
        "sourceRevision": os.getenv("GITHUB_SHA", "local"),
        "encryption": {
            "scheme": "PBKDF2-HMAC-SHA256 + AES-256-GCM",
            "passwordSource": "PAF_ARCHIVE_PASSWORD",
            "passwordIncluded": False,
        },
        "archives": entries,
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (output / "SHA256SUMS").write_text(
        "".join(f"{entry['sha256']}  {entry['asset']}\n" for entry in entries),
        encoding="utf-8",
    )
    notes = [
        "# Private Agent Factory agent archives",
        "",
        f"Built from revision `{manifest['sourceRevision']}`.",
        "",
        "Each PAF was generated from the reviewable `workflow.json` source, decrypted in memory, and compared byte-for-byte at the JSON payload level before publication.",
        "",
        "The archives are workflow-only. Configure the target model, REST data source, credentials, and Agent Memory settings after import. Obtain the common archive passphrase through the approved secret-sharing channel.",
        "",
        "## Assets",
        "",
        *[
            f"- `{entry['asset']}` — {entry['application']['name']} / "
            f"{entry['name']} (flow v{entry['workflowVersion']})"
            for entry in entries
        ],
        "",
        "Use `SHA256SUMS` to verify downloaded assets and `manifest.json` for machine-readable provenance.",
        "",
    ]
    (output / "RELEASE_NOTES.md").write_text("\n".join(notes), encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    password_source = parser.add_mutually_exclusive_group()
    password_source.add_argument("--password-env", default="PAF_ARCHIVE_PASSWORD")
    password_source.add_argument("--password-file", type=Path)
    args = parser.parse_args()
    if args.password_file:
        try:
            password = args.password_file.read_text(encoding="utf-8").rstrip("\r\n")
        except OSError as exc:
            print(f"error: cannot read password file: {exc}", file=sys.stderr)
            return 2
    else:
        password = os.getenv(args.password_env)
    if not password:
        print(f"error: password environment variable '{args.password_env}' is not set", file=sys.stderr)
        return 2
    try:
        manifest = build_release(args.root, args.output, password)
    except (OSError, PafError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"Built and round-trip validated {len(manifest['archives'])} archive(s) in {args.output}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
