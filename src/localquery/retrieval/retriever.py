from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer
from rank_bm25 import BM25Okapi
import numpy as np

class HybridRetriever:
    def __init__(self, embedding_model_name: str = 'all-MiniLM-L6-v2'):
        """
        Initializes the Hybrid Retriever with dense and sparse capabilities.
        Note: The embedding model will be downloaded on first run.
        """
        self.encoder = SentenceTransformer(embedding_model_name)
        self.documents = []
        self.dense_index = None
        self.bm25_index = None
        self.tokenized_corpus = []

    def index(self, documents: List[str]):
        """
        Indexes a list of documents (schema fragments, descriptions, examples)
        for both dense and sparse retrieval.
        """
        self.documents = documents
        
        # Dense Indexing
        if documents:
            self.dense_index = self.encoder.encode(documents, convert_to_tensor=True)
            
            # Sparse Indexing (BM25)
            self.tokenized_corpus = [doc.lower().split(" ") for doc in documents]
            self.bm25_index = BM25Okapi(self.tokenized_corpus)
        else:
            self.dense_index = None
            self.bm25_index = None

    def retrieve(self, query: str, top_k: int = 3, rrf_k: int = 60) -> List[str]:
        """
        Retrieves the top_k most relevant documents using Reciprocal Rank Fusion (RRF)
        to combine dense and sparse rankings.
        """
        if not self.documents:
            return []

        # 1. Dense Retrieval
        query_embedding = self.encoder.encode(query, convert_to_tensor=True)
        # Using dot product/cosine similarity depending on sentence-transformers defaults
        from sentence_transformers import util
        dense_scores = util.cos_sim(query_embedding, self.dense_index)[0]
        
        # Sort indices by score descending
        dense_ranked_indices = np.argsort(-dense_scores.cpu().numpy())

        # 2. Sparse Retrieval (BM25)
        tokenized_query = query.lower().split(" ")
        bm25_scores = self.bm25_index.get_scores(tokenized_query)
        bm25_ranked_indices = np.argsort(-bm25_scores)

        # 3. Reciprocal Rank Fusion (RRF)
        # RRF_score = 1 / (rrf_k + rank)
        rrf_scores = {i: 0.0 for i in range(len(self.documents))}
        
        for rank, doc_idx in enumerate(dense_ranked_indices):
            rrf_scores[doc_idx] += 1.0 / (rrf_k + rank + 1)
            
        for rank, doc_idx in enumerate(bm25_ranked_indices):
            rrf_scores[doc_idx] += 1.0 / (rrf_k + rank + 1)

        # Sort combined scores
        sorted_indices = sorted(rrf_scores, key=rrf_scores.get, reverse=True)
        
        # Return top_k
        return [self.documents[i] for i in sorted_indices[:top_k]]
