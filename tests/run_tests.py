"""
LocalQuery Test Runner
========================
Runs all tests using unittest (no pytest installation required).
Alternatively run via: pytest tests/ -v

Usage::

    python tests/run_tests.py
"""

import sys
import os
import unittest

# Add src/ to the path so localquery is importable without pip install
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

_TEST_DIR = os.path.dirname(__file__)


# ---------------------------------------------------------------------------
# Test: ClarificationEngine
# ---------------------------------------------------------------------------

class TestClarificationEngine(unittest.TestCase):

    def setUp(self):
        from localquery.clarification.engine import ClarificationEngine
        self.engine = ClarificationEngine()

    def test_recent_triggers(self):
        self.assertIsNotNone(self.engine.needs_clarification("Show recent transactions"))

    def test_lately_triggers(self):
        self.assertIsNotNone(self.engine.needs_clarification("What happened lately?"))

    def test_last_year_triggers(self):
        self.assertIsNotNone(self.engine.needs_clarification("Revenue last year?"))

    def test_last_quarter_triggers(self):
        self.assertIsNotNone(self.engine.needs_clarification("Sales last quarter"))

    def test_revenue_triggers(self):
        self.assertIsNotNone(self.engine.needs_clarification("How much revenue?"))

    def test_active_users_triggers(self):
        self.assertIsNotNone(self.engine.needs_clarification("List all active users"))

    def test_top_users_triggers(self):
        self.assertIsNotNone(self.engine.needs_clarification("Show the top users"))

    def test_no_trigger_for_specific_query(self):
        self.assertIsNone(self.engine.needs_clarification("Show users signed up in 2023"))

    def test_no_trigger_for_balance_query(self):
        self.assertIsNone(self.engine.needs_clarification("Show total balance in savings"))

    def test_custom_heuristic(self):
        self.engine.add_heuristic(lambda q: "Custom?" if "secret" in q else None)
        self.assertEqual(self.engine.needs_clarification("What is the secret?"), "Custom?")


# ---------------------------------------------------------------------------
# Test: DBExecutor
# ---------------------------------------------------------------------------

_EXECUTOR_DB = os.path.join(_TEST_DIR, "_run_tests_executor.db")


class TestDBExecutor(unittest.TestCase):

    def setUp(self):
        from localquery.db.schema import setup_db
        if os.path.exists(_EXECUTOR_DB):
            os.remove(_EXECUTOR_DB)
        setup_db(_EXECUTOR_DB)

    def tearDown(self):
        if os.path.exists(_EXECUTOR_DB):
            try:
                os.remove(_EXECUTOR_DB)
            except OSError:
                pass

    def test_execution(self):
        from localquery.db.executor import DBExecutor
        executor = DBExecutor(db_path=_EXECUTOR_DB)
        res = executor.execute_query("SELECT first_name, status FROM users LIMIT 2")
        self.assertIsNone(res["error"])
        self.assertIn("first_name", res["columns"])
        self.assertEqual(len(res["rows"]), 2)

    def test_security(self):
        from localquery.db.executor import DBExecutor
        executor = DBExecutor(db_path=_EXECUTOR_DB)
        res = executor.execute_query("DROP TABLE users")
        self.assertEqual(res["error"], "Only SELECT queries are allowed.")

    def test_formatting(self):
        from localquery.db.executor import DBExecutor
        executor = DBExecutor(db_path=_EXECUTOR_DB)
        res = executor.execute_query("SELECT user_id, email FROM users LIMIT 1")
        formatted = executor.format_results(res)
        self.assertIn("|", formatted)
        self.assertIn("user_id", formatted)

    def test_empty_result(self):
        from localquery.db.executor import DBExecutor
        executor = DBExecutor(db_path=_EXECUTOR_DB)
        res = executor.execute_query("SELECT * FROM users WHERE 1=0")
        self.assertIsNone(res["error"])
        formatted = executor.format_results(res)
        self.assertEqual(formatted, "No results found.")


# ---------------------------------------------------------------------------
# Test: Pipeline (multi-turn clarification)
# ---------------------------------------------------------------------------

_PIPELINE_DB = os.path.join(_TEST_DIR, "_run_tests_pipeline.db")


class TestPipelineClarification(unittest.TestCase):

    def setUp(self):
        from localquery.db.schema import setup_db
        if os.path.exists(_PIPELINE_DB):
            os.remove(_PIPELINE_DB)
        setup_db(_PIPELINE_DB)

    def tearDown(self):
        if os.path.exists(_PIPELINE_DB):
            try:
                os.remove(_PIPELINE_DB)
            except OSError:
                pass

    def test_multi_turn_clarification_state(self):
        from unittest.mock import patch, MagicMock

        with patch("localquery.retrieval.retriever.SentenceTransformer"), \
             patch("localquery.retrieval.retriever.BM25Okapi"), \
             patch("localquery.orchestration.pipeline.LocalLLMClient") as mock_llm:

            from localquery.orchestration.pipeline import LocalQueryPipeline
            from localquery.retrieval.retriever import HybridRetriever

            # Patch the retriever's index/retrieve to be no-ops
            with patch.object(HybridRetriever, "index"), \
                 patch.object(HybridRetriever, "retrieve", return_value=["schema"]):

                pipeline = LocalQueryPipeline(db_path=_PIPELINE_DB)

                res = pipeline.process_query("Show recent transactions")
                self.assertEqual(res["status"], "needs_clarification")
                self.assertEqual(pipeline.pending_clarification_query, "Show recent transactions")

                mock_llm.return_value.generate_sql.return_value = "SELECT * FROM transactions LIMIT 5"
                pipeline.llm_client = mock_llm.return_value

                res2 = pipeline.process_query("last 30 days")
                self.assertEqual(res2["status"], "success")
                self.assertEqual(res2["sql"], "SELECT * FROM transactions LIMIT 5")
                self.assertIsNone(pipeline.pending_clarification_query)

    def test_session_history_recorded(self):
        """After a query, session_history should have one entry."""
        from unittest.mock import patch, MagicMock
        from localquery.orchestration.pipeline import LocalQueryPipeline
        from localquery.retrieval.retriever import HybridRetriever

        with patch.object(HybridRetriever, "index"), \
             patch.object(HybridRetriever, "retrieve", return_value=["schema"]):

            pipeline = LocalQueryPipeline(db_path=_PIPELINE_DB)
            pipeline.llm_client = MagicMock()
            pipeline.llm_client.generate_sql.return_value = "SELECT * FROM users"

            pipeline.process_query("List all users")
            self.assertEqual(len(pipeline.session_history), 1)
            self.assertEqual(pipeline.session_history[0]["status"], "success")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Discover and run all tests in this file
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    for cls in [TestClarificationEngine, TestDBExecutor, TestPipelineClarification]:
        suite.addTests(loader.loadTestsFromTestCase(cls))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
