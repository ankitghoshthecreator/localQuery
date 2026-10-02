"""
LocalQuery Orchestration Pipeline
===================================
Ties together the Clarification Engine, Hybrid Retriever, Local LLM,
and DB Executor into a single end-to-end query processing flow.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from localquery.clarification.engine import ClarificationEngine
from localquery.db.executor import DBExecutor
from localquery.db.schema import extract_schema_from_db
from localquery.llm.client import LocalLLMClient
from localquery.retrieval.retriever import HybridRetriever


class LocalQueryPipeline:
    """
    End-to-end pipeline for answering natural language questions against a
    local SQLite database.

    Flow::

        user_question
            → ClarificationEngine  (ambiguous? → ask follow-up)
            → HybridRetriever      (dense + BM25 + RRF schema retrieval)
            → LocalLLMClient       (SQL generation)
            → DBExecutor           (safe SELECT execution)
            → formatted result

    Args:
        db_path:    Absolute or relative path to the SQLite database file.
        model_name: Name of the Ollama model to use for SQL generation.
        top_k:      Number of schema fragments to retrieve per query (default 4).
    """

    def __init__(
        self,
        db_path: str,
        model_name: str = "qwen2.5-coder:3b",
        top_k: int = 4,
    ):
        self.db_path = db_path
        self.top_k = top_k

        self.clarification_engine = ClarificationEngine()
        self.retriever = HybridRetriever()
        self.llm_client = LocalLLMClient(model_name=model_name)
        self.db_executor = DBExecutor(db_path=db_path)

        # Stateful multi-turn support
        self.pending_clarification_query: Optional[str] = None
        self.session_history: List[Dict[str, Any]] = []

        # Index the schema on startup
        print(f"  Indexing schema for: {db_path}")
        schema_docs = extract_schema_from_db(db_path)
        if not schema_docs:
            raise ValueError(f"No tables found in database: {db_path}")
        self.retriever.index(schema_docs)
        print(f"  Indexed {len(schema_docs)} table(s). Pipeline ready.\n")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process_query(self, user_question: str) -> Dict[str, Any]:
        """
        Process a single user question through the full pipeline.

        Args:
            user_question: Raw string from the user.

        Returns:
            A result dict with keys:
              - status           : "success" | "needs_clarification" | "error"
              - clarification_question : str or None
              - sql              : str or None
              - data             : dict with 'columns', 'rows', 'error' — or None
              - formatted_result : markdown table string or None
              - error            : error message string or None
        """
        result: Dict[str, Any] = {
            "status": "success",
            "clarification_question": None,
            "sql": None,
            "data": None,
            "formatted_result": None,
            "error": None,
        }

        try:
            # --- Multi-turn: user is answering a pending clarification ---
            if self.pending_clarification_query:
                combined = (
                    f"{self.pending_clarification_query} "
                    f"(Clarification: {user_question})"
                )
                self.pending_clarification_query = None
                return self._execute_rag_flow(combined, result)

            # --- Step 1: Clarification check ---
            clarification = self.clarification_engine.needs_clarification(user_question)
            if clarification:
                self.pending_clarification_query = user_question
                result["status"] = "needs_clarification"
                result["clarification_question"] = clarification
                self._record_history(user_question, result)
                return result

            # --- Steps 2–4: RAG → SQL → Execute ---
            return self._execute_rag_flow(user_question, result)

        except Exception as exc:
            self.pending_clarification_query = None
            result["status"] = "error"
            result["error"] = str(exc)
            self._record_history(user_question, result)
            return result

    @property
    def history(self) -> List[Dict[str, Any]]:
        """Returns the list of processed query results for this session."""
        return self.session_history

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _execute_rag_flow(
        self, query: str, result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Runs retrieval → LLM → execution and populates *result* in-place."""

        # Step 2: Hybrid retrieval
        context = self.retriever.retrieve(query, top_k=self.top_k)

        # Step 3: LLM SQL generation
        sql = self.llm_client.generate_sql(query, context)

        if sql.startswith("Error") or sql.upper().startswith("ERROR:"):
            result["status"] = "error"
            result["error"] = sql
            self._record_history(query, result)
            return result

        result["sql"] = sql

        # Step 4: DB execution
        db_result = self.db_executor.execute_query(sql)
        if db_result["error"]:
            result["status"] = "error"
            result["error"] = db_result["error"]
            self._record_history(query, result)
            return result

        result["data"] = db_result
        result["formatted_result"] = self.db_executor.format_results(db_result)
        self._record_history(query, result)
        return result

    def _record_history(self, query: str, result: Dict[str, Any]) -> None:
        """Append a lightweight history entry for the session."""
        self.session_history.append(
            {
                "query": query,
                "status": result["status"],
                "sql": result.get("sql"),
            }
        )
