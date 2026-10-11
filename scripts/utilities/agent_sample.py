#!/usr/bin/env python3
"""Extract reviewable agent sources and build password-protected PAF archives."""

from __future__ import annotations

import argparse
import base64
import binascii
import copy
import getpass
import io
import json
import os
import re
import shutil
import sys
import uuid
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

try:
    from cryptography.exceptions import InvalidTag
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
except ImportError:  # pragma: no cover - exercised only in an unprepared environment
    InvalidTag = None  # type: ignore[assignment]
    AESGCM = None  # type: ignore[assignment]
    PBKDF2HMAC = None  # type: ignore[assignment]
    hashes = None  # type: ignore[assignment]


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_APPLICATION_VERSION = "26.7.0.0.0"
PBKDF2_ITERATIONS = 100_000
KEY_BYTES = 32
SALT_BYTES = 16
IV_BYTES = 12
TAG_BYTES = 16
MAX_PAF_BYTES = 100 * 1024 * 1024
MAX_ENTRY_BYTES = 25 * 1024 * 1024
MAX_UNCOMPRESSED_BYTES = 100 * 1024 * 1024
REQUIRED_FLOW_FIELDS = (
    "name",
    "description",
    "category",
    "icon",
    "published",
    "flowGraph",
    "data",
)


class PafError(ValueError):
    """Raised when a PAF archive or flow payload is invalid."""


@dataclass(frozen=True)
class PafArchive:
    metadata: dict[str, Any]
    flows: tuple[tuple[str, dict[str, Any]], ...]


def _require_cryptography() -> None:
    if AESGCM is None or PBKDF2HMAC is None or hashes is None:
        raise PafError(
            "the 'cryptography' package is required; run "
            "'python -m pip install -r scripts/requirements.txt'"
        )


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().casefold()).strip("-")
    if not slug:
        raise PafError("the agent name does not contain any usable filename characters")
    return slug


def _archive_name_component(value: Any, fallback: str) -> str:
    text = str(value or fallback)
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", text).strip("_")
    return cleaned or fallback


def validate_flow(flow: Any, source: str = "workflow.json") -> dict[str, Any]:
    if not isinstance(flow, dict):
        raise PafError(f"{source}: flow payload must be a JSON object")

    missing = [field for field in REQUIRED_FLOW_FIELDS if field not in flow]
    if missing:
        raise PafError(f"{source}: missing required field(s): {', '.join(missing)}")

    for field in ("name", "description"):
        if not isinstance(flow[field], str) or not flow[field].strip():
            raise PafError(f"{source}: '{field}' must be a non-empty string")
    category = flow["category"]
    if not (
        isinstance(category, str)
        or (isinstance(category, int) and not isinstance(category, bool))
    ):
        raise PafError(f"{source}: 'category' must be a string or integer")
    if not isinstance(flow["icon"], str):
        raise PafError(f"{source}: 'icon' must be a string")
    for field in ("published", "flowGraph"):
        if not isinstance(flow[field], bool):
            raise PafError(f"{source}: '{field}' must be a boolean")
    if flow["data"] is None:
        raise PafError(f"{source}: 'data' must contain the visual flow graph")
    return flow


def _derive_key(password: str, salt: bytes) -> bytes:
    _require_cryptography()
    if not password:
        raise PafError("the archive password cannot be empty")
    kdf = PBKDF2HMAC(  # type: ignore[operator]
        algorithm=hashes.SHA256(),  # type: ignore[union-attr]
        length=KEY_BYTES,
        salt=salt,
        iterations=PBKDF2_ITERATIONS,
    )
    return kdf.derive(password.encode("utf-8"))


def encrypt_zip_bytes(zip_payload: bytes, password: str) -> bytes:
    """Return Base64(salt || IV || AES-GCM ciphertext || tag)."""
    _require_cryptography()
    salt = os.urandom(SALT_BYTES)
    iv = os.urandom(IV_BYTES)
    key = _derive_key(password, salt)
    ciphertext_and_tag = AESGCM(key).encrypt(iv, zip_payload, None)  # type: ignore[misc]
    return base64.b64encode(salt + iv + ciphertext_and_tag)


def decrypt_paf_bytes(paf_payload: bytes, password: str) -> bytes:
    """Decrypt a PAF payload using the documented Agent Builder envelope."""
    _require_cryptography()
    if len(paf_payload) > MAX_PAF_BYTES:
        raise PafError(f"archive exceeds the {MAX_PAF_BYTES // (1024 * 1024)} MiB limit")
    compact_payload = b"".join(paf_payload.split())
    try:
        envelope = base64.b64decode(compact_payload, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise PafError("archive is not valid Base64") from exc

    minimum_size = SALT_BYTES + IV_BYTES + TAG_BYTES
    if len(envelope) < minimum_size:
        raise PafError("archive encryption envelope is truncated")
    salt = envelope[:SALT_BYTES]
    iv = envelope[SALT_BYTES : SALT_BYTES + IV_BYTES]
    ciphertext_and_tag = envelope[SALT_BYTES + IV_BYTES :]
    key = _derive_key(password, salt)
    try:
        return AESGCM(key).decrypt(iv, ciphertext_and_tag, None)  # type: ignore[misc]
    except InvalidTag as exc:  # type: ignore[misc]
        raise PafError("incorrect password or archive authentication failed") from exc


def _safe_zip_members(archive: zipfile.ZipFile) -> list[zipfile.ZipInfo]:
    infos = archive.infolist()
    total_size = 0
    seen: set[str] = set()
    for info in infos:
        path = PurePosixPath(info.filename)
        if path.is_absolute() or ".." in path.parts or "\\" in info.filename:
            raise PafError(f"unsafe archive member path: {info.filename}")
        if info.filename in seen:
            raise PafError(f"duplicate archive member: {info.filename}")
        seen.add(info.filename)
        if info.file_size > MAX_ENTRY_BYTES:
            raise PafError(f"archive member is too large: {info.filename}")
        total_size += info.file_size
        if total_size > MAX_UNCOMPRESSED_BYTES:
            raise PafError("archive uncompressed size exceeds the safety limit")
    return infos


def _read_json_member(archive: zipfile.ZipFile, name: str) -> Any:
    try:
        raw = archive.read(name)
    except KeyError as exc:
        raise PafError(f"archive is missing {name}") from exc
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PafError(f"{name}: invalid UTF-8 JSON: {exc}") from exc


def parse_zip_bytes(zip_payload: bytes) -> PafArchive:
    try:
        with zipfile.ZipFile(io.BytesIO(zip_payload), "r") as archive:
            infos = _safe_zip_members(archive)
            broken_member = archive.testzip()
            if broken_member:
                raise PafError(f"ZIP integrity check failed for {broken_member}")
            names = {info.filename for info in infos if not info.is_dir()}
            if "metadata.json" not in names:
                raise PafError("archive is missing metadata.json")
            metadata = _read_json_member(archive, "metadata.json")
            if not isinstance(metadata, dict):
                raise PafError("metadata.json must contain a JSON object")

            flow_names = sorted(
                name
                for name in names
                if len(PurePosixPath(name).parts) == 2
                and PurePosixPath(name).parts[0] == "flows"
                and PurePosixPath(name).suffix.lower() == ".json"
            )
            if not flow_names:
                raise PafError("archive does not contain any flows/*.json payloads")
            flows = tuple(
                (name, validate_flow(_read_json_member(archive, name), name))
                for name in flow_names
            )
    except zipfile.BadZipFile as exc:
        raise PafError("decrypted payload is not a valid ZIP archive") from exc
    return PafArchive(metadata=metadata, flows=flows)


def read_paf(path: Path, password: str) -> PafArchive:
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise PafError(f"cannot read {path}: {exc}") from exc
    return parse_zip_bytes(decrypt_paf_bytes(payload, password))


def build_metadata(
    application_version: str,
    flow_count: int,
    base: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build documented metadata, or preserve metadata from an actual UI export."""
    if base is not None:
        metadata = copy.deepcopy(base)
        if not isinstance(metadata, dict):
            raise PafError("archive metadata must be a JSON object")
        return metadata

    if not application_version.strip():
        raise PafError("application version cannot be empty")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return {
        "applicationVersion": application_version,
        "exportedAt": timestamp,
        "encrypted": True,
        "contains": {
            "customFlows": True,
            "modelDetails": False,
            "dbDataSources": False,
            "selectAiDetails": False,
            "mcpServers": False,
            "restApiTools": False,
        },
        "count": flow_count,
        "flowScope": "selected",
    }


def build_zip_bytes(
    flows: list[dict[str, Any]],
    metadata: dict[str, Any],
) -> bytes:
    if not flows:
        raise PafError("at least one flow is required")
    for index, flow in enumerate(flows):
        validate_flow(flow, f"flow {index + 1}")

    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "metadata.json",
            json.dumps(metadata, indent=2, ensure_ascii=False) + "\n",
        )
        for index, flow in enumerate(flows, start=1):
            identifier = _archive_name_component(
                flow.get("id")
                or flow.get("agent_id")
                or flow.get("workflowId")
                or flow.get("originWorkflowId"),
                str(uuid.uuid4()),
            )
            name = _archive_name_component(flow.get("name"), f"flow_{index}")
            archive.writestr(
                f"flows/{identifier}_{name}.json",
                json.dumps(flow, indent=2, ensure_ascii=False) + "\n",
            )
    return output.getvalue()


def build_paf_bytes(
    flows: list[dict[str, Any]],
    password: str,
    application_version: str = DEFAULT_APPLICATION_VERSION,
    metadata: dict[str, Any] | None = None,
) -> tuple[bytes, dict[str, Any]]:
    archive_metadata = build_metadata(application_version, len(flows), metadata)
    zip_payload = build_zip_bytes(flows, archive_metadata)
    return encrypt_zip_bytes(zip_payload, password), archive_metadata


def _load_json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise PafError(f"cannot read {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise PafError(f"{path}: invalid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise PafError(f"{label} must contain a JSON object")
    return value


def _password(env_name: str | None, confirm: bool) -> str:
    if env_name:
        value = os.getenv(env_name)
        if value is None:
            raise PafError(f"password environment variable '{env_name}' is not set")
        if not value:
            raise PafError(f"password environment variable '{env_name}' is empty")
        return value

    value = getpass.getpass("PAF archive password: ")
    if not value:
        raise PafError("the archive password cannot be empty")
    if confirm:
        confirmation = getpass.getpass("Confirm PAF archive password: ")
        if value != confirmation:
            raise PafError("password confirmation does not match")
    return value


def _sample_readme(name: str, description: str, paf_name: str) -> str:
    return f"""# {name}

{description}

## Complete this source-first scaffold

1. Add a reviewed `sample.json` with prerequisites, tools, safety controls, setup, demo turns, expected outcomes, and validation evidence.
2. Add only sanitized, distributable dependencies under `assets/`.
3. Run the tests and documentation generator.
4. Build the encrypted release asset with `python scripts/build_release.py`.

## Contents

- `workflow.json` — exact serialized Agent Builder custom-flow payload
- `archive-metadata.json` — archive metadata retained for compatible rebuilds
- `slides/` — presentation and demo material
- `assets/` — supporting files safe to distribute with the sample

The generated `{paf_name}` is published as a release asset and must not be committed.
"""


def _write_sample_folder(
    root: Path,
    application: str,
    folder_name: str,
    flow: dict[str, Any],
    metadata: dict[str, Any],
    overwrite: bool,
) -> Path:
    application_slug = slugify(application)
    folder_slug = slugify(folder_name)
    root = root.resolve()
    folder = root / application_slug / folder_slug
    if folder.exists() and any(folder.iterdir()) and not overwrite:
        raise PafError(
            f"{folder} already exists and is not empty; use --overwrite to replace managed files"
        )
    folder.mkdir(parents=True, exist_ok=True)

    paf_name = f"{slugify(flow['name'])}.paf"
    (folder / "workflow.json").write_text(
        json.dumps(flow, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (folder / "archive-metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (folder / "README.md").write_text(
        _sample_readme(flow["name"], flow["description"], paf_name),
        encoding="utf-8",
    )
    slides = folder / "slides"
    assets = folder / "assets"
    slides.mkdir(exist_ok=True)
    assets.mkdir(exist_ok=True)
    if not (slides / "README.md").exists():
        (slides / "README.md").write_text(
            "# Slides\n\nAdd the agent overview or demo PowerPoint deck here.\n",
            encoding="utf-8",
        )
    if not (assets / "README.md").exists():
        (assets / "README.md").write_text(
            "# Assets\n\nAdd distributable supporting files for this agent here.\n",
            encoding="utf-8",
        )
    return folder


def create_from_paf(args: argparse.Namespace) -> int:
    password = _password(args.password_env, confirm=False)
    paf_path = args.paf.resolve()
    archive = read_paf(paf_path, password)
    if len(archive.flows) != 1:
        names = ", ".join(flow["name"] for _, flow in archive.flows)
        raise PafError(
            f"{paf_path} contains {len(archive.flows)} flows ({names}); "
            "export exactly one flow per repository sample"
        )
    _, flow = archive.flows[0]
    folder = _write_sample_folder(
        args.root,
        args.application,
        args.folder or flow["name"],
        flow,
        archive.metadata,
        args.overwrite,
    )
    print(f"Created {folder}")
    return 0


def create_from_spec(args: argparse.Namespace) -> int:
    spec_path = args.agent_spec.resolve()
    flow = validate_flow(_load_json_object(spec_path, "workflow"), str(spec_path))
    metadata = build_metadata(args.application_version, 1)
    folder = _write_sample_folder(
        args.root,
        args.application,
        args.folder or flow["name"],
        flow,
        metadata,
        args.overwrite,
    )
    print(f"Created {folder}")
    return 0


def pack(args: argparse.Namespace) -> int:
    folder = args.agent_folder.resolve()
    if not folder.is_dir():
        raise PafError(f"agent folder does not exist: {folder}")
    spec_path = folder / "workflow.json"
    flow = validate_flow(_load_json_object(spec_path, "workflow"), str(spec_path))
    metadata_path = args.metadata or folder / "archive-metadata.json"
    metadata: dict[str, Any] | None = None
    if metadata_path.is_file():
        metadata = _load_json_object(metadata_path, "archive metadata")

    password = _password(args.password_env, confirm=True)
    paf_payload, used_metadata = build_paf_bytes(
        [flow],
        password,
        application_version=args.application_version,
        metadata=metadata,
    )
    release_asset = f"{slugify(flow['name'])}.paf"
    manifest_path = folder / "sample.json"
    if manifest_path.is_file():
        manifest = _load_json_object(manifest_path, "sample manifest")
        artifacts = manifest.get("artifacts")
        if not isinstance(artifacts, dict):
            raise PafError(f"{manifest_path}: artifacts must be an object")
        release_asset = artifacts.get("releaseAsset")
        if (
            not isinstance(release_asset, str)
            or Path(release_asset).name != release_asset
            or not release_asset.endswith(".paf")
        ):
            raise PafError(f"{manifest_path}: artifacts.releaseAsset must be a PAF filename")
    repository_root = (
        folder.parents[2]
        if folder.parent.parent.name == "agents"
        else folder.parent
    )
    output = (args.output or repository_root / "dist" / release_asset).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(paf_payload)
    (folder / "archive-metadata.json").write_text(
        json.dumps(used_metadata, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Created {output}")
    return 0


def inspect_archive(args: argparse.Namespace) -> int:
    password = _password(args.password_env, confirm=False)
    archive = read_paf(args.paf.resolve(), password)
    version = next(
        (
            archive.metadata[key]
            for key in ("application_version", "applicationVersion", "app_version", "version")
            if key in archive.metadata
        ),
        None,
    )
    summary = {
        "applicationVersion": version,
        "metadataKeys": sorted(archive.metadata),
        "flowCount": len(archive.flows),
        "flows": [
            {
                "archivePath": name,
                "name": flow["name"],
                "description": flow["description"],
                "category": flow["category"],
                "published": flow["published"],
            }
            for name, flow in archive.flows
        ],
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


def _add_password_option(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--password-env",
        metavar="VARIABLE",
        help="Read the password from this environment variable instead of prompting.",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    from_paf = subparsers.add_parser(
        "create-from-paf", help="Create an agent folder from a single-flow UI export."
    )
    from_paf.add_argument("paf", type=Path)
    from_paf.add_argument("--root", type=Path, default=REPOSITORY_ROOT / "agents")
    from_paf.add_argument(
        "--application",
        required=True,
        help="Application name used to create the parent folder.",
    )
    from_paf.add_argument("--folder", help="Override the generated folder name.")
    from_paf.add_argument("--overwrite", action="store_true")
    _add_password_option(from_paf)
    from_paf.set_defaults(handler=create_from_paf)

    from_spec = subparsers.add_parser(
        "create-from-spec", help="Create a source-first folder from workflow JSON."
    )
    from_spec.add_argument("agent_spec", type=Path)
    from_spec.add_argument("--root", type=Path, default=REPOSITORY_ROOT / "agents")
    from_spec.add_argument(
        "--application",
        required=True,
        help="Application name used to create the parent folder.",
    )
    from_spec.add_argument("--folder", help="Override the generated folder name.")
    from_spec.add_argument(
        "--application-version", default=DEFAULT_APPLICATION_VERSION
    )
    from_spec.add_argument("--overwrite", action="store_true")
    from_spec.set_defaults(handler=create_from_spec)

    pack_parser = subparsers.add_parser(
        "pack", help="Build a PAF from an existing source-first agent folder."
    )
    pack_parser.add_argument("agent_folder", type=Path)
    pack_parser.add_argument("--output", type=Path)
    pack_parser.add_argument("--metadata", type=Path)
    pack_parser.add_argument(
        "--application-version", default=DEFAULT_APPLICATION_VERSION
    )
    _add_password_option(pack_parser)
    pack_parser.set_defaults(handler=pack)

    inspect_parser = subparsers.add_parser(
        "inspect", help="Validate an archive and print a safe summary."
    )
    inspect_parser.add_argument("paf", type=Path)
    _add_password_option(inspect_parser)
    inspect_parser.set_defaults(handler=inspect_archive)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.handler(args)
    except (OSError, PafError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

