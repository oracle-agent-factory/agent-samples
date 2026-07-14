from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.generate_docs import build_site


class DocumentationGeneratorTests(unittest.TestCase):
    def test_catalog_uses_agent_spec_description_and_escapes_html(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            folder = root / "research-assistant"
            folder.mkdir()
            (folder / "agent-spec.json").write_text(
                json.dumps(
                    {
                        "name": "Research <Assistant>",
                        "description": "Grounded <script>alert('no')</script> research.",
                        "category": "Productivity",
                        "version": "1.0",
                    }
                ),
                encoding="utf-8",
            )
            (folder / "README.md").write_text("# Research Assistant\n", encoding="utf-8")
            (folder / "research-assistant.paf").write_bytes(b"test")
            slides = folder / "slides"
            slides.mkdir()
            (slides / "overview.pptx").write_bytes(b"test")
            output = root / "docs"

            agents = build_site(
                root,
                output,
                "https://github.example/repository/tree/main",
            )
            page = (output / "index.html").read_text(encoding="utf-8")
            catalog = json.loads((output / "agents.json").read_text(encoding="utf-8"))

        self.assertEqual(1, len(agents))
        self.assertIn("Grounded &lt;script&gt;", page)
        self.assertNotIn("<script>alert", page)
        self.assertEqual("Research <Assistant>", catalog["agents"][0]["name"])
        self.assertTrue(catalog["agents"][0]["has_paf"])
        self.assertTrue(catalog["agents"][0]["has_slides"])

    def test_missing_description_fails_the_build(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            folder = root / "invalid-agent"
            folder.mkdir()
            (folder / "agent-spec.json").write_text(
                json.dumps({"name": "Invalid Agent"}), encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "description"):
                build_site(root, root / "docs")


if __name__ == "__main__":
    unittest.main()

