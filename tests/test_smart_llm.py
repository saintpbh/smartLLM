"""Unit tests for SMART LLM core pipeline components."""

from __future__ import annotations

import unittest
from pathlib import Path
from smart_llm.detect import detect_files
from smart_llm.extract import extract_files
from smart_llm.build import build_graph, serialize_graph
from smart_llm.cluster import cluster_graph
from smart_llm.embed import SimpleSemanticVectorizer, DenseIndex
from smart_llm.query import classify_query, query_codebase

class TestSmartLLMPipeline(unittest.TestCase):

    def test_query_classifier(self):
        """Test Query Gateway classification heuristics."""
        self.assertEqual(classify_query("quicksort algorithm in python"), "general")
        self.assertEqual(classify_query("how does login authentication work in smart-llm"), "codebase")
        self.assertEqual(classify_query("what is ast"), "codebase")

    def test_semantic_vectorizer(self):
        """Test pure-NumPy fallback TF-IDF vectorizer."""
        import numpy as np
        documents = [
            "authenticator manages user session login and token authentication validation",
            "database query handler writes records to postgres sql tables",
            "file reader loads markdown text and extracts frontmatter tags"
        ]
        
        vectorizer = SimpleSemanticVectorizer()
        vectorizer.fit(documents)
        
        self.assertTrue(vectorizer.fitted)
        expected_vocab_len = len({w for w in " ".join(documents).lower().split() if len(w) > 2})
        self.assertEqual(len(vectorizer.vocab), expected_vocab_len)
        
        # Check normalization
        v = vectorizer.embed_query("user login")
        norm = float(np.linalg.norm(v))
        self.assertAlmostEqual(norm, 1.0)

    def test_dense_index(self):
        """Test dense indexing and searching."""
        doc_map = {
            "auth.py": "class UserManager handles authentication logic, tokens, and database login verification",
            "db.py": "def save_user stores user row in database SQL connection pool",
            "utils.py": "helper functions to split strings and sanitize user inputs"
        }
        
        index = DenseIndex()
        index.build_index(doc_map)
        
        # Search query matching auth.py
        results = index.search("UserManager auth logic", top_k=2)
        self.assertTrue(len(results) > 0)
        self.assertEqual(results[0][0], "auth.py")

    def test_query_pipeline(self):
        """Test the end-to-end query retrieval pipeline with classification and relevance gate."""
        doc_map = {
            "auth.py": "class UserManager handles authentication logic, tokens, and database login verification",
            "db.py": "def save_user stores user row in database SQL connection pool"
        }
        
        # Query that is general should skip codebase context
        res_general = query_codebase("how to print hello world in python", doc_map)
        self.assertTrue("skipped" in res_general["gateway_status"])
        self.assertEqual(res_general["context"], "")
        
        # Query that matches auth.py
        res_auth = query_codebase("UserManager verification logic", doc_map)
        self.assertTrue("approved" in res_auth["gateway_status"])
        self.assertTrue("auth.py" in res_auth["context"])

if __name__ == "__main__":
    unittest.main()
