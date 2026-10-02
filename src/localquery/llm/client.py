"""
LocalQuery LLM Client
======================
Wraps the Ollama local inference API to generate SQL from natural language.
Includes robust prompt engineering and SQL extraction heuristics.
"""

from __future__ import annotations

import re
from typing import List

import ollama


_SYSTEM_PROMPT = """\
You are LocalQuery, an expert SQLite SQL assistant.
Your ONLY job is to write a single valid SQLite SELECT query based on the user's question and the provided schema.

Rules:
1. Return ONLY the raw SQL query — no markdown fences, no explanations, no comments.
2. Never use INSERT, UPDATE, DELETE, DROP, ALTER, or CREATE.
3. Always use table and column names exactly as shown in the schema.
4. If a JOIN is needed, write it explicitly — never use implicit joins.
5. Always add a LIMIT clause (default: LIMIT 50) unless the user asks for all results.
6. If the question cannot be answered with the given schema, return: ERROR: <reason>
"""


class LocalLLMClient:
    """Client for communicating with a locally-running Ollama model."""

    def __init__(self, model_name: str = "qwen2.5-coder:3b"):
        self.model_name = model_name

    def generate_sql(self, question: str, schema_context: List[str]) -> str:
        """
        Generates a SQLite SELECT query from a natural language question
        and retrieved schema context.

        Args:
            question: The user's natural language question (possibly with
                      clarification appended).
            schema_context: List of schema fragment strings from the retriever.

        Returns:
            A SQL string, or a string starting with "Error" on failure.
        """
        context_str = "\n\n".join(schema_context)

        prompt = (
            f"Schema Context:\n{context_str}\n\n"
            f"User Question: {question}\n\n"
            "SQL Query (SELECT only, no markdown):"
        )

        try:
            response = ollama.generate(
                model=self.model_name,
                prompt=prompt,
                system=_SYSTEM_PROMPT,
                options={"temperature": 0.0},  # deterministic for SQL
            )
            raw = response.get("response", "").strip()
            return self._clean_sql(raw)

        except Exception as e:
            # Surface a helpful message so the pipeline can show it to the user
            return f"Error connecting to Ollama: {e}"

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _clean_sql(raw: str) -> str:
        """
        Strips markdown code fences and surrounding whitespace from the
        model's output, in case it ignored the formatting instructions.
        """
        # Remove ```sql ... ``` or ``` ... ``` fences
        raw = re.sub(r"^```(?:sql)?\s*", "", raw, flags=re.IGNORECASE | re.MULTILINE)
        raw = re.sub(r"```\s*$", "", raw, flags=re.MULTILINE)

        # If the model returned multiple statements, take only the first SELECT
        statements = [s.strip() for s in raw.split(";") if s.strip()]
        for stmt in statements:
            if stmt.upper().startswith("SELECT"):
                return stmt.strip()

        # Fall back to the raw stripped output
        return raw.strip()
