from __future__ import annotations

import argparse
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.utilities.agent_sample import (
    PafError,
    build_paf_bytes,
    create_from_spec,
    read_paf,
    validate_flow,
)


def sample_flow() -> dict[str, object]:
    return {
        "id": "sample-001",
        "name": "Research Assistant",
        "description": "Finds and summarizes grounded research.",
        "category": "Productivity",
        "icon": "search",
        "published": False,
        "flowGraph": True,
        "data": {"nodes": [], "edges": []},
    }


class PafArchiveTests(unittest.TestCase):
    def test_password_protected_archive_round_trip(self) -> None:
        payload, metadata = build_paf_bytes(
            [sample_flow()], "correct horse battery staple", "26.4.0.0.0"
        )
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "sample.paf"
            path.write_bytes(payload)
            archive = read_paf(path, "correct horse battery staple")

        self.assertEqual(metadata, archive.metadata)
        self.assertEqual(1, len(archive.flows))
        self.assertEqual("26.4.0.0.0", metadata["applicationVersion"])
        self.assertTrue(metadata["contains"]["customFlows"])
        self.assertFalse(metadata["contains"]["restApiTools"])
        self.assertEqual("Research Assistant", archive.flows[0][1]["name"])

    def test_wrong_password_is_rejected(self) -> None:
        payload, _ = build_paf_bytes([sample_flow()], "right-password")
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "sample.paf"
            path.write_bytes(payload)
            with self.assertRaisesRegex(PafError, "authentication failed"):
                read_paf(path, "wrong-password")

    def test_incomplete_flow_is_rejected(self) -> None:
        flow = sample_flow()
        del flow["flowGraph"]
        with self.assertRaisesRegex(PafError, "flowGraph"):
            validate_flow(flow)

    def test_current_server_numeric_category_is_accepted(self) -> None:
        flow = sample_flow()
        flow["category"] = 1
        flow["workflowId"] = "server-flow-001"
        self.assertEqual(flow, validate_flow(flow))

    def test_create_from_spec_scaffolds_agent_folder(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            spec = root / "input.json"
            spec.write_text(json.dumps(sample_flow()), encoding="utf-8")
            args = argparse.Namespace(
                agent_spec=spec,
                root=root / "catalog",
                application="Test Application",
                folder=None,
                application_version="26.4.0.0.0",
                overwrite=False,
                password_env="TEST_PAF_PASSWORD",
            )
            self.assertEqual(0, create_from_spec(args))

            folder = (
                root
                / "catalog"
                / "test-application"
                / "research-assistant"
            )
            self.assertFalse((folder / "research-assistant.paf").exists())
            self.assertTrue((folder / "workflow.json").is_file())
            self.assertTrue((folder / "archive-metadata.json").is_file())
            self.assertTrue((folder / "README.md").is_file())
            self.assertTrue((folder / "slides" / "README.md").is_file())
            self.assertTrue((folder / "assets" / "README.md").is_file())


if __name__ == "__main__":
    unittest.main()

