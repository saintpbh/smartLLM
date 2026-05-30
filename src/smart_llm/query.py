"""Query Gateway, Hybrid Search (RRF), and Context Assembly."""

from __future__ import annotations

import re
import numpy as np
from pathlib import Path
from rank_bm25 import BM25Okapi
from smart_llm.embed import DenseIndex

# --- 1. Query Gateway Classifier ---
GENERAL_KEYWORDS = {
    "quicksort", "bubble sort", "binary search", "regex", "regular expression",
    "how to", "what is", "difference between", "tutorial", "example of"
}

CODEBASE_KEYWORDS = {
    "project", "module", "codebase", "architecture", "folder", "structure",
    "design", "setup", "run", "build", "ingest", "query", "gateway",
    "mindvault", "smart-llm", "ast", "tree-sitter", "extract", "embedding"
}

def classify_query(query: str) -> str:
    """Classify user query as 'codebase' or 'general' using keyword heuristics.
    
    If it is general, we skip workspace context injection to prevent token pollution.
    """
    query_lower = query.lower()
    cleaned = re.sub(r"[^\w\s]", " ", query_lower).split()
    query_set = set(cleaned)
    
    codebase_matches = query_set.intersection(CODEBASE_KEYWORDS)
    has_file_reference = any(ext in query_lower for ext in [".py", ".md", ".ts", ".js", "/", "\\"])
    
    # 1. Prioritize codebase if codebase keywords or files are present
    if codebase_matches or has_file_reference:
        return "codebase"
        
    # 2. Match general multi-word phrases next
    for gk in GENERAL_KEYWORDS:
        if gk in query_lower:
            return "general"
            
    general_matches = query_set.intersection(GENERAL_KEYWORDS)
    if general_matches:
        return "general"
        
    return "codebase"  # Default fallback is codebase-related for safety

# --- 2. BM25 Searcher Helper ---
class BM25Searcher:
    def __init__(self, doc_map: dict[str, str]):
        self.doc_ids = list(doc_map.keys())
        self.corpus = list(doc_map.values())
        self.tokenized_corpus = [self._tokenize(doc) for doc in self.corpus]
        
        if self.tokenized_corpus:
            # Prevent BM25 from zeroing out weights on very small corpora (N < 5)
            tokenized_with_dummies = list(self.tokenized_corpus)
            if len(tokenized_with_dummies) < 5:
                for idx in range(5 - len(tokenized_with_dummies)):
                    tokenized_with_dummies.append([f"__dummy_word_{idx}__"])
            self.bm25 = BM25Okapi(tokenized_with_dummies)
        else:
            self.bm25 = None

    def _tokenize(self, text: str) -> list[str]:
        return re.sub(r"[^\w\s]", " ", text.lower()).split()

    def search(self, query: str, top_k: int = 5) -> list[tuple[str, float]]:
        if not self.bm25:
            return []
        tokenized_query = self._tokenize(query)
        scores = self.bm25.get_scores(tokenized_query)
        sorted_indices = np.argsort(scores)[::-1][:top_k]
        return [(self.doc_ids[idx], float(scores[idx])) for idx in sorted_indices if scores[idx] > 0]

# --- 3. Reciprocal Rank Fusion (RRF) ---
def reciprocal_rank_fusion(
    bm25_results: list[tuple[str, float]],
    vector_results: list[tuple[str, float]],
    k: int = 60
) -> list[tuple[str, float]]:
    """Merges two ranked lists of search results using Reciprocal Rank Fusion (RRF)."""
    rrf_scores: dict[str, float] = {}
    
    # Process BM25
    for rank, (doc_id, _) in enumerate(bm25_results):
        rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + (1.0 / (k + rank + 1))
        
    # Process Vector Search
    for rank, (doc_id, _) in enumerate(vector_results):
        rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + (1.0 / (k + rank + 1))
        
    # Sort results by descending RRF score
    sorted_results = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
    return sorted_results

# --- 4. Relevance Gateway ---
RELEVANCE_THRESHOLD = 0.025  # Minimum RRF score to permit context injection

# --- 5. Main Query Pipeline ---
def query_codebase(
    user_query: str,
    doc_map: dict[str, str],
    graph: dict | None = None,
    budget_chars: int = 4000
) -> dict:
    """The 3-layer Smart Memory Retrieval: Search -> Graph -> Wiki under budget control."""
    # Step 1: Gateway Classification
    classification = classify_query(user_query)
    if classification == "general":
        return {
            "gateway_status": "skipped (classified as general coding question)",
            "context": "",
            "search_results": []
        }

    if not doc_map:
        return {
            "gateway_status": "empty codebase",
            "context": "",
            "search_results": []
        }

    # Step 2: Hybrid Search
    # 2.1 Sparse Search (BM25)
    bm25_searcher = BM25Searcher(doc_map)
    bm25_results = bm25_searcher.search(user_query, top_k=10)
    
    # 2.2 Dense Search (Embeddings)
    dense_index = DenseIndex()
    dense_index.build_index(doc_map)
    vector_results = dense_index.search(user_query, top_k=10)
    
    # 2.3 Rank Fusion via RRF
    hybrid_results = reciprocal_rank_fusion(bm25_results, vector_results)
    
    if not hybrid_results:
        return {
            "gateway_status": "no relevant search matches found",
            "context": "",
            "search_results": []
        }

    # Step 3: Relevance Gate
    top_doc_id, top_score = hybrid_results[0]
    if top_score < RELEVANCE_THRESHOLD:
        return {
            "gateway_status": f"skipped (highest match score {top_score:.4f} below relevance threshold {RELEVANCE_THRESHOLD})",
            "context": "",
            "search_results": []
        }

    # Step 4: Graph Expansion (Optional BFS/DFS check if graph is supplied)
    related_docs = [doc_id for doc_id, _ in hybrid_results[:3]]
    if graph and "links" in graph:
        # Simple graph expansion: find files connected to our top files
        for link in graph.get("links", []):
            src = link.get("source", "")
            tgt = link.get("target", "")
            # If source file is in our top matches, pull target file
            if src in related_docs and tgt not in related_docs:
                related_docs.append(tgt)
            elif tgt in related_docs and src not in related_docs:
                related_docs.append(src)
                
    # Step 5: Wiki Context Concatenation & strict budget limits
    context_parts = []
    char_count = 0
    
    for doc_id in related_docs:
        content = doc_map.get(doc_id, "")
        if not content.strip():
            continue
            
        header = f"### Component Memory: {doc_id}\n"
        wrapped_content = f"{header}{content}\n\n"
        
        if char_count + len(wrapped_content) > budget_chars:
            remaining_budget = budget_chars - char_count - len(header) - 10
            if remaining_budget > 100:
                context_parts.append(f"{header}{content[:remaining_budget]}...\n[TRUNCATED TO FIT BUDGET]\n\n")
            break
            
        context_parts.append(wrapped_content)
        char_count += len(wrapped_content)

    final_context = "".join(context_parts)
    
    return {
        "gateway_status": "approved & injected",
        "context": final_context,
        "search_results": [(doc_id, float(score)) for doc_id, score in hybrid_results[:5]]
    }
