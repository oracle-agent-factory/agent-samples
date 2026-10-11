from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.generate_docs import build_site


def write_sample(root: Path, summary: str = "Grounded <script>alert('no')</script> research.") -> Path:
    folder = root / "agents" / "test-application" / "research-assistant"
    (folder / "assets").mkdir(parents=True)
    workflow = {"name": "Research <Assistant>", "version": 4}
    (folder / "workflow.json").write_text(json.dumps(workflow), encoding="utf-8")
    (folder / "archive-metadata.json").write_text(json.dumps({"applicationVersion": "26.7.0.0.0"}), encoding="utf-8")
    (folder / "assets" / "instructions.md").write_text("Instructions", encoding="utf-8")
    (folder / "assets" / "openapi.json").write_text("{}", encoding="utf-8")
    (folder / "README.md").write_text("# Research Assistant", encoding="utf-8")
    manifest = {
        "schemaVersion": "1.0",
        "slug": "research-assistant",
        "application": {"slug": "test-application", "name": "Test Application"},
        "useCase": {"slug": "research-assistant", "name": "Research assistance"},
        "title": workflow["name"],
        "summary": summary,
        "category": "Productivity",
        "version": "4",
        "platform": {"applicationVersion": "26.7.0.0.0"},
        "connectionContext": "Static test context.",
        "memory": {"mode": "implicit", "crossThread": True, "description": "Learns corrections."},
        "capabilities": ["Grounded research."],
        "prerequisites": ["A test connection."],
        "tools": [{"name": "Search", "method": "GET", "path": "/search", "purpose": "Find records."}],
        "safetyControls": ["Read only."],
        "setup": ["Configure the connection."],
        "demo": {"sessions": [{"title": "Test", "steps": [{"speaker": "User", "text": "Find it."}]}], "expectedOutcomes": ["A grounded answer."]},
        "validation": {"date": "2026-10-11", "environment": "Test", "status": "Passed", "notes": []},
        "artifacts": {"workflow": "workflow.json", "archiveMetadata": "archive-metadata.json", "instructions": "assets/instructions.md", "openapi": "assets/openapi.json", "releaseAsset": "research-assistant.paf"},
    }
    (folder / "sample.json").write_text(json.dumps(manifest), encoding="utf-8")
    return folder


class DocumentationGeneratorTests(unittest.TestCase):
    def test_catalog_and_detail_page_are_generated_and_escape_html(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            write_sample(root)
            output = root / "docs"
            agents = build_site(root, output, "https://github.example/repository/tree/main", "https://github.example/repository/releases/download/latest")
            index = (output / "index.html").read_text(encoding="utf-8")
            detail = (
                output / "agents" / "test-application" / "research-assistant" / "index.html"
            ).read_text(encoding="utf-8")
            catalog = json.loads((output / "agents.json").read_text(encoding="utf-8"))
        self.assertEqual(1, len(agents))
        self.assertIn("Grounded &lt;script&gt;", index)
        self.assertNotIn("<script>alert", index)
        self.assertIn("Download encrypted PAF", detail)
        self.assertIn("releases/download/latest/research-assistant.paf", detail)
        self.assertIn("Tested demo flow", detail)
        self.assertEqual("Research <Assistant>", catalog["agents"][0]["name"])
        self.assertEqual("Test Application", catalog["agents"][0]["application_name"])
        self.assertEqual("Research assistance", catalog["agents"][0]["use_case_name"])
        self.assertIn("agents/test-application/research-assistant/workflow.json", detail)

    def test_missing_required_documentation_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            folder = write_sample(root)
            manifest = json.loads((folder / "sample.json").read_text(encoding="utf-8"))
            manifest["capabilities"] = []
            (folder / "sample.json").write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "capabilities"):
                build_site(root, root / "docs")

    def test_workflow_version_must_match_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            folder = write_sample(root)
            manifest = json.loads((folder / "sample.json").read_text(encoding="utf-8"))
            manifest["version"] = "5"
            (folder / "sample.json").write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "title and version"):
                build_site(root, root / "docs")

    def test_application_slug_must_match_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            folder = write_sample(root)
            manifest = json.loads((folder / "sample.json").read_text(encoding="utf-8"))
            manifest["application"]["slug"] = "wrong-application"
            (folder / "sample.json").write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "application.slug"):
                build_site(root, root / "docs")


if __name__ == "__main__":
    unittest.main()
