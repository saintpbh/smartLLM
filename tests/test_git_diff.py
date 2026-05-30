"""Unit tests for Git-diff parsing, incremental indexing, and dynamic rule compiling."""

from __future__ import annotations

import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
from smart_llm.git_diff import get_git_changes, incremental_update_graph
from smart_llm.sync import compile_agents_doc

class TestGitDiffAndSync(unittest.TestCase):

    @patch("subprocess.run")
    def test_get_git_changes(self, mock_run):
        """Test parsing of git status output."""
        mock_result = MagicMock()
        mock_result.stdout = (
            " M src/smart_llm/cli.py\n"
            "?? src/smart_llm/new_file.py\n"
            " D tests/old_test.py\n"
            " M node_modules/ignored/file.js\n"  # Skipped directory
        )
        mock_run.return_value = mock_result

        # Mock existence of .git directory
        with patch.object(Path, "exists", return_value=True):
            changes = get_git_changes(Path("/dummy/project"))
            
        self.assertEqual(changes["modified"], ["src/smart_llm/cli.py", "src/smart_llm/new_file.py"])
        self.assertEqual(changes["deleted"], ["tests/old_test.py"])

    def test_incremental_graph_update(self):
        """Test that modified file nodes replace old ones, keeping clean nodes."""
        existing_graph = {
            "nodes": [
                {"id": "src__smart_llm__cli_py::module::cli", "source_file": "/proj/src/smart_llm/cli.py"},
                {"id": "src__smart_llm__query_py::module::query", "source_file": "/proj/src/smart_llm/query.py"}
            ],
            "links": [
                {"source": "src__smart_llm__cli_py::module::cli", "target": "src__smart_llm__query_py::module::query", "source_file": "/proj/src/smart_llm/cli.py"}
            ]
        }

        changes = {
            "modified": ["src/smart_llm/cli.py"],
            "deleted": []
        }

        # Mock extraction results for the modified file (empty nodes for simple testing)
        with patch("smart_llm.extract.extract_files", return_value={"nodes": [{"id": "src__smart_llm__cli_py::module::cli", "source_file": "/proj/src/smart_llm/cli.py", "label": "new_cli"}], "edges": []}):
            updated = incremental_update_graph(existing_graph, changes, Path("/proj"))

        # Clean node (query.py) must remain
        node_ids = [n["id"] for n in updated["nodes"]]
        self.assertIn("src__smart_llm__query_py::module::query", node_ids)
        self.assertIn("src__smart_llm__cli_py::module::cli", node_ids)
        
        # Modified cli node should have the new attributes (label: "new_cli")
        cli_node = [n for n in updated["nodes"] if n["id"] == "src__smart_llm__cli_py::module::cli"][0]
        self.assertEqual(cli_node.get("label"), "new_cli")

        # Dirty link from modified cli.py must be removed
        self.assertEqual(len(updated["links"]), 0)

    def test_compile_agents_doc(self):
        """Test rule compiler formats modular communities correctly."""
        graph_data = {
            "nodes": [
                {"id": "src__smart_llm__query_py::module::query", "file_type": "code"}
            ],
            "links": []
        }

        wiki_doc_map = {
            "wiki/community_0.md": (
                "# Community Memory 0\n"
                "**Cohesion Score**: 0.450\n\n"
                "## Component Members\n"
                "- **query** (module) — `[[query]]`"
            )
        }

        compiled = compile_agents_doc(Path("/proj"), graph_data, wiki_doc_map)
        
        self.assertIn("Community 0", compiled)
        self.assertIn("Cohesion: 0.450", compiled)
        self.assertIn("query", compiled)

if __name__ == "__main__":
    unittest.main()
