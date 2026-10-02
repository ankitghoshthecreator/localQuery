"""
LocalQuery Hybrid Retriever
============================
Combines dense semantic embeddings (sentence-transformers) with sparse
BM25 keyword matching using Reciprocal Rank Fusion (RRF) to retrieve the
most relevant schema fragments for a given user query.
"""

from __future__ import annotations

import re
from typing import List, Optional

import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer, util


def _tokenize(text: str) -> List[str]:
    """
    Simple tokenizer: lower-case, split on non-alphanumeric characters,
    and filter out empty tokens.  Better than naive split() for SQL DDL.
    """
    return [tok for tok in re.split(r"[^a-z0-9_]+", text.lower()) if tok]


class HybridRetriever:
    """
    Retrieves relevant schema documents using a hybrid dense + sparse approach.

    - **Dense**:  Cosine similarity via a sentence-transformer embedding model.
    - **Sparse**: BM25 Okapi keyword matching.
    - **Fusion**: Reciprocal Rank Fusion (RRF) to combine both ranked lists.

    Args:
        embedding_model_name: HuggingFace model name for dense embeddings.
                              Defaults to ``'all-MiniLM-L6-v2'``.
    """

    def __init__(self, embedding_model_name: str = "all-MiniLM-L6-v2"):
        self.encoder = SentenceTransformer(embedding_model_name)
        self.documents: List[str] = []
        self.dense_index: Optional[object] = None  # tensor
        self.bm25_index: Optional[BM25Okapi] = None
        self._tokenized_corpus: List[List[str]] = []

    # ------------------------------------------------------------------
    # Indexing
    # ------------------------------------------------------------------

    def index(self, documents: List[str]) -> None:
        """
        Build dense and sparse indexes from *documents*.

        Calling ``index()`` a second time replaces the previous corpus.

        Args:
            documents: List of strings to index (e.g. schema DDL fragments).
        """
        self.documents = documents

        if not documents:
            self.dense_index = None
            self.bm25_index = None
            self._tokenized_corpus = []
            return

        # Dense index
        self.dense_index = self.encoder.encode(documents, convert_to_tensor=True)

        # Sparse index
        self._tokenized_corpus = [_tokenize(doc) for doc in documents]
        self.bm25_index = BM25Okapi(self._tokenized_corpus)

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def retrieve(self, query: str, top_k: int = 3, rrf_k: int = 60) -> List[str]:
        """
        Retrieve the *top_k* most relevant documents for *query* using RRF.

        Args:
            query:  The natural language (or SQL-flavoured) query string.
            top_k:  Maximum number of documents to return.
            rrf_k:  RRF constant — higher values reduce the impact of top ranks.

        Returns:
            List of at most *top_k* document strings, sorted by relevance.
        """
        if not self.documents:
            return []

        n = len(self.documents)
        top_k = min(top_k, n)

        # --- Dense retrieval ---
        query_emb = self.encoder.encode(query, convert_to_tensor=True)
        dense_scores = util.cos_sim(query_emb, self.dense_index)[0]
        dense_ranked = np.argsort(-dense_scores.cpu().numpy())

        # --- Sparse retrieval (BM25) ---
        bm25_scores = self.bm25_index.get_scores(_tokenize(query))
        bm25_ranked = np.argsort(-bm25_scores)

        # --- Reciprocal Rank Fusion ---
        rrf_scores = {i: 0.0 for i in range(n)}
        for rank, doc_idx in enumerate(dense_ranked):
            rrf_scores[int(doc_idx)] += 1.0 / (rrf_k + rank + 1)
        for rank, doc_idx in enumerate(bm25_ranked):
            rrf_scores[int(doc_idx)] += 1.0 / (rrf_k + rank + 1)

        sorted_indices = sorted(rrf_scores, key=rrf_scores.__getitem__, reverse=True)
        return [self.documents[i] for i in sorted_indices[:top_k]]
