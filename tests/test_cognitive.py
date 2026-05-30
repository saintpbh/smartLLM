"""Unit tests for SMART LLM Phase 3 Cognitive Memory Engine components."""

from __future__ import annotations

import unittest
import networkx as nx
from pathlib import Path
from smart_llm.proactive import predict_next_targets
from smart_llm.consolidate import prune_and_consolidate_graph
from smart_llm.synopsis import build_community_synopsis
from smart_llm.broker import _count_parameters, _find_calls_and_arg_counts
from tree_sitter import Language, Parser

class TestCognitiveEngine(unittest.TestCase):

    def test_proactive_prefetch_prediction(self):
        """Test neighbors prediction based on focus file and adjacency."""
        G = nx.DiGraph()
        # Add mock nodes representing files
        G.add_node("src__smart_llm__cli_py::module::cli", source_file="/proj/src/smart_llm/cli.py")
        G.add_node("src__smart_llm__query_py::module::query", source_file="/proj/src/smart_llm/query.py")
        G.add_node("src__smart_llm__embed_py::module::embed", source_file="/proj/src/smart_llm/embed.py")
        G.add_node("src__smart_llm__other_py::module::other", source_file="/proj/src/smart_llm/other.py")
        
        # Add edges showing calling relationships (cli calls query, query calls embed)
        G.add_edge("src__smart_llm__cli_py::module::cli", "src__smart_llm__query_py::module::query")
        G.add_edge("src__smart_llm__query_py::module::query", "src__smart_llm__embed_py::module::embed")
        
        # Predict next files from focus: cli.py
        preds = predict_next_targets(G, "src/smart_llm/cli.py", top_k=2)
        
        self.assertTrue(len(preds) > 0)
        # First degree neighbor (query.py) should be predicted first
        self.assertEqual(preds[0][0], "src/smart_llm/query.py")
        # Second degree neighbor (embed.py) should be predicted next
        self.assertEqual(preds[1][0], "src/smart_llm/embed.py")

    def test_sleep_phase_pruning(self):
        """Test pruning of isolated placeholder nodes during consolidation."""
        G = nx.DiGraph()
        G.add_node("real_node", file_type="code")
        G.add_node("isolated_placeholder", file_type="placeholder")
        G.add_node("linked_placeholder", file_type="placeholder")
        
        G.add_edge("real_node", "linked_placeholder")
        
        self.assertEqual(G.number_of_nodes(), 3)
        
        G_pruned = prune_and_consolidate_graph(G)
        
        self.assertEqual(G_pruned.number_of_nodes(), 2)
        self.assertIn("real_node", G_pruned)
        self.assertIn("linked_placeholder", G_pruned)
        self.assertNotIn("isolated_placeholder", G_pruned)

    def test_community_synopsis_fallback(self):
        """Test that synopsis fallback correctly infers software domain from names."""
        members = [
            "src__smart_llm__query_py::function::query_codebase",
            "src__smart_llm__query_py::class::bm25searcher"
        ]
        
        synopsis = build_community_synopsis(3, members, {"links": []})
        self.assertIn("RRF", synopsis)
        self.assertIn("검색", synopsis)

    def test_ast_broker_signature_counting(self):
        """Test parameter and argument parsing using mock AST structures."""
        import tree_sitter_python
        lang = Language(tree_sitter_python.language())
        parser = Parser(lang)
        
        # Definition
        code_def = b"def save_user(username, email, verbose=False):\n    pass"
        tree_def = parser.parse(code_def)
        func_node = tree_def.root_node.children[0]
        
        total, required = _count_parameters(func_node, ".py")
        self.assertEqual(total, 3)
        self.assertEqual(required, 2)  # verbose has default, so only 2 required parameters
        
        # Call
        code_call = b"save_user('alice')"
        tree_call = parser.parse(code_call)
        calls = _find_calls_and_arg_counts(tree_call.root_node, ".py")
        
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0], "save_user")
        self.assertEqual(calls[0][1], 1)  # Only 1 argument provided

if __name__ == "__main__":
    unittest.main()
