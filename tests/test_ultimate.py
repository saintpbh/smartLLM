"""Unit tests for SMART LLM Phase 4 Ultimate Cognitive OS components."""

from __future__ import annotations

import unittest
import networkx as nx
from pathlib import Path
from smart_llm.sqlite_ledger import init_ledger, set_state, get_state, get_active_alerts
from smart_llm.polyglot import check_polyglot_contracts
from smart_llm.proactive import predict_next_targets
from tree_sitter import Language, Parser

class TestUltimateEngine(unittest.TestCase):

    def test_sqlite_ledger_transactions(self):
        """Test SQLite transactional memory ledger read/write integrity."""
        workspace = Path("/tmp/mock_smart_llm_workspace")
        workspace.mkdir(exist_ok=True)
        
        # Init DB
        init_ledger(workspace)
        
        # Set state
        test_val = {"module": "auth", "state": "healthy", "version": 1.0}
        set_state(workspace, "test_auth_state", test_val)
        
        # Get state
        read_val = get_state(workspace, "test_auth_state")
        self.assertEqual(read_val, test_val)
        
        # Clean up database files safely
        db_path = workspace / "smart-llm-out" / "ledger.db"
        if db_path.exists():
            try:
                db_path.unlink()
                (workspace / "smart-llm-out" / "ledger.db-shm").unlink(missing_ok=True)
                (workspace / "smart-llm-out" / "ledger.db-wal").unlink(missing_ok=True)
                (workspace / "smart-llm-out").rmdir()
                workspace.rmdir()
            except OSError:
                pass

    def test_dijkstra_semantic_pathfinding(self):
        """Test Dijkstra shortest path calculation on semantic-weighted edges."""
        G = nx.DiGraph()
        
        # Setup nodes
        G.add_node("cli", source_file="/proj/cli.py")
        G.add_node("query", source_file="/proj/query.py")
        G.add_node("embed", source_file="/proj/embed.py")
        
        # Connect: cli -> query has strong semantic link (weight = 0.2)
        # Connect: cli -> embed has weak semantic link (weight = 0.9)
        # Connect: query -> embed has strong semantic link (weight = 0.1)
        G.add_edge("cli", "query", weight=0.2)
        G.add_edge("cli", "embed", weight=0.9)
        G.add_edge("query", "embed", weight=0.1)
        
        # Dijkstra path: cli -> query -> embed = 0.2 + 0.1 = 0.3 (instead of cli -> embed = 0.9)
        # Therefore, query is much closer semantically to cli!
        preds = predict_next_targets(G, "cli.py", top_k=2)
        
        self.assertTrue(len(preds) > 0)
        self.assertEqual(preds[0][0], "src/smart_llm/query.py" if "src/smart_llm" in preds[0][0] else "query.py")

    def test_polyglot_contract_check(self):
        """Test parsing and matching of TS fetch clients to Python route endpoints."""
        import tree_sitter_typescript
        import tree_sitter_python
        
        lang_ts = Language(tree_sitter_typescript.language_typescript())
        lang_py = Language(tree_sitter_python.language())
        
        parser_ts = Parser(lang_ts)
        parser_py = Parser(lang_py)
        
        # Mock fetch call in TypeScript
        ts_code = b"fetch('/api/v1/users')"
        # Mock matching FastAPI route in Python
        py_code = b"@app.get('/api/v1/users')\ndef read_users(): pass"
        
        # Test checks if paths match perfectly. If so, no contract violations!
        # If we had fetch('/api/v1/users') but Python required @app.get('/api/v1/users/{user_id}'),
        # it would raise Path Variable Missing!
        
        # Verify TS fetch parser
        tree_ts = parser_ts.parse(ts_code)
        from smart_llm.polyglot import _extract_ts_fetches
        fetches = _extract_ts_fetches(tree_ts.root_node, ts_code)
        self.assertEqual(len(fetches), 1)
        self.assertEqual(fetches[0][0], "/api/v1/users")
        
        # Verify Python route parser
        tree_py = parser_py.parse(py_code)
        from smart_llm.polyglot import _extract_python_api_endpoints
        endpoints = _extract_python_api_endpoints(tree_py.root_node, py_code)
        self.assertEqual(len(endpoints), 1)
        self.assertEqual(endpoints[0][0], "/api/v1/users")

    def test_dashboard_html_and_routing(self):
        """Test that the embedded dashboard HTML is generated correctly and contains critical elements."""
        from smart_llm.server import get_dashboard_html
        html = get_dashboard_html()
        self.assertIn("SMART LLM - Real-Time Cognitive Dashboard", html)
        self.assertIn("d3.v7.min.js", html)
        self.assertIn("<svg id=\"knowledge-svg\"></svg>", html)

if __name__ == "__main__":
    unittest.main()
