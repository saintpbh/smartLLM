"""Vector embeddings and local semantic dense vector search."""

from __future__ import annotations

import re
import numpy as np

class SimpleSemanticVectorizer:
    """A pure-numpy TF-IDF vectorizer used as a robust fallback for semantic matching without external downloads."""
    
    def __init__(self):
        self.vocab: dict[str, int] = {}
        self.idf: np.ndarray = np.array([])
        self.fitted = False

    def _tokenize(self, text: str) -> list[str]:
        cleaned = re.sub(r"[^\w\s]", " ", text.lower())
        return [w for w in cleaned.split() if len(w) > 2]

    def fit(self, documents: list[str]) -> SimpleSemanticVectorizer:
        if not documents:
            return self
        
        # Build vocabulary
        vocab_set = set()
        doc_tokens = []
        for doc in documents:
            tokens = self._tokenize(doc)
            doc_tokens.append(tokens)
            vocab_set.update(tokens)
            
        self.vocab = {word: idx for idx, word in enumerate(sorted(vocab_set))}
        vocab_size = len(self.vocab)
        
        if vocab_size == 0:
            return self

        # Calculate IDF
        doc_count = len(documents)
        df = np.zeros(vocab_size)
        for tokens in doc_tokens:
            unique_tokens = set(tokens)
            for t in unique_tokens:
                if t in self.vocab:
                    df[self.vocab[t]] += 1
                    
        self.idf = np.log((1 + doc_count) / (1 + df)) + 1
        self.fitted = True
        return self

    def transform(self, documents: list[str]) -> np.ndarray:
        if not self.fitted or len(self.vocab) == 0:
            return np.zeros((len(documents), 1))
            
        vocab_size = len(self.vocab)
        vectors = np.zeros((len(documents), vocab_size))
        
        for doc_idx, doc in enumerate(documents):
            tokens = self._tokenize(doc)
            for t in tokens:
                if t in self.vocab:
                    vectors[doc_idx, self.vocab[t]] += 1
            
            # Multiply by IDF
            vectors[doc_idx] = vectors[doc_idx] * self.idf
            
            # L2 normalization
            norm = np.linalg.norm(vectors[doc_idx])
            if norm > 0:
                vectors[doc_idx] /= norm
                
        return vectors

    def embed_query(self, query: str) -> np.ndarray:
        return self.transform([query])[0]


class DenseIndex:
    """A lightweight FAISS-like dense vector indexer using NumPy."""
    
    def __init__(self):
        self.vectorizer = SimpleSemanticVectorizer()
        self.doc_ids: list[str] = []
        self.documents: list[str] = []
        self.embeddings: np.ndarray = np.array([])

    def build_index(self, doc_map: dict[str, str]) -> None:
        """Build the vector index from a map of doc_id -> doc_content."""
        self.doc_ids = list(doc_map.keys())
        self.documents = list(doc_map.values())
        
        if not self.documents:
            return
            
        # Try local sentence-transformers if installed
        try:
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer("all-MiniLM-L6-v2")
            self.embeddings = model.encode(self.documents, convert_to_numpy=True)
            # Normalize for cosine similarity
            norms = np.linalg.norm(self.embeddings, axis=1, keepdims=True)
            self.embeddings = self.embeddings / np.where(norms > 0, norms, 1.0)
            self.is_sentence_transformer = True
        except ImportError:
            # Fallback to simple semantic vectorizer
            self.vectorizer.fit(self.documents)
            self.embeddings = self.vectorizer.transform(self.documents)
            self.is_sentence_transformer = False

    def search(self, query: str, top_k: int = 5) -> list[tuple[str, float]]:
        """Search query against document embeddings and return list of (doc_id, score)."""
        if len(self.doc_ids) == 0:
            return []
            
        try:
            if getattr(self, "is_sentence_transformer", False):
                from sentence_transformers import SentenceTransformer
                model = SentenceTransformer("all-MiniLM-L6-v2")
                query_vector = model.encode([query], convert_to_numpy=True)[0]
                norm = np.linalg.norm(query_vector)
                if norm > 0:
                    query_vector /= norm
            else:
                query_vector = self.vectorizer.embed_query(query)
        except Exception:
            # Emergency fallback
            query_vector = self.vectorizer.embed_query(query)

        if query_vector.shape[0] != self.embeddings.shape[1]:
            # Dimension mismatch safeguard
            return []

        # Cosine similarity is simple dot product as vectors are pre-normalized
        scores = np.dot(self.embeddings, query_vector)
        
        # Sort scores in descending order
        sorted_indices = np.argsort(scores)[::-1][:top_k]
        
        return [(self.doc_ids[idx], float(scores[idx])) for idx in sorted_indices]
