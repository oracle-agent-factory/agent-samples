from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_release import build_release
from scripts.utilities.agent_sample import read_paf


class ReleaseBuilderTests(unittest.TestCase):
    def test_builds_and_round_trip_validates_release_archive(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            folder = root / "agents" / "sample-application" / "sample-use-case"
            folder.mkdir(parents=True)
            flow = {
                "workflowId": "sample-001",
                "name": "Sample Agent",
                "description": "A release test.",
                "category": 1,
                "icon": "search",
                "published": False,
                "flowGraph": True,
                "data": {"nodes": [], "edges": []},
                "version": 2,
            }
            metadata = {
                "applicationVersion": "26.7.0.0.0",
                "encrypted": True,
                "contains": {"customFlows": True, "restApiTools": False},
                "count": 1,
                "flowScope": "selected",
            }
            sample = {
                "slug": "sample-agent",
                "application": {
                    "slug": "sample-application",
                    "name": "Sample Application",
                },
                "useCase": {
                    "slug": "sample-use-case",
                    "name": "Sample use case",
                },
                "artifacts": {
                    "workflow": "workflow.json",
                    "archiveMetadata": "archive-metadata.json",
                    "releaseAsset": "sample-agent.paf",
                },
            }
            (folder / "workflow.json").write_text(json.dumps(flow), encoding="utf-8")
            (folder / "archive-metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
            (folder / "sample.json").write_text(json.dumps(sample), encoding="utf-8")
            output = root / "dist"
            manifest = build_release(root, output, "release-test-password")
            archive_path = output / "sample-agent.paf"
            archive = read_paf(archive_path, "release-test-password")
            digest = hashlib.sha256(archive_path.read_bytes()).hexdigest()

            self.assertEqual(flow, archive.flows[0][1])
            self.assertEqual(digest, manifest["archives"][0]["sha256"])
            self.assertEqual(
                "agents/sample-application/sample-use-case",
                manifest["archives"][0]["sourcePath"],
            )
            self.assertEqual(
                "Sample Application",
                manifest["archives"][0]["application"]["name"],
            )
            self.assertIn("sample-agent.paf", (output / "SHA256SUMS").read_text(encoding="utf-8"))
            self.assertTrue((output / "RELEASE_NOTES.md").is_file())


if __name__ == "__main__":
    unittest.main()
