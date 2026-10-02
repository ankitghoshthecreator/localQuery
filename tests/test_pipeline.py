import os
import pytest
from unittest.mock import MagicMock, patch
from localquery.orchestration.pipeline import LocalQueryPipeline
from localquery.db.schema import setup_db

# Use a fixed path inside the project that the sandbox can write to
_TEST_DB = os.path.join(os.path.dirname(__file__), "_test_pipeline.db")


@pytest.fixture(autouse=True)
def temp_db():
    """Set up and tear down a test finance database in the tests directory."""
    if os.path.exists(_TEST_DB):
        os.remove(_TEST_DB)
    setup_db(_TEST_DB)
    yield _TEST_DB
    if os.path.exists(_TEST_DB):
        try:
            os.remove(_TEST_DB)
        except OSError:
            pass


@patch("localquery.orchestration.pipeline.LocalLLMClient")
def test_pipeline_clarification_flow(mock_llm_cls):
    """Test multi-turn clarification: ambiguous query → follow-up → resolved query."""
    pipeline = LocalQueryPipeline(db_path=_TEST_DB)

    # Query needing clarification
    res = pipeline.process_query("Show recent transactions")
    assert res["status"] == "needs_clarification"
    assert res["clarification_question"] is not None
    assert pipeline.pending_clarification_query == "Show recent transactions"

    # User provides clarification — wire in a mock LLM response
    mock_llm_cls.return_value.generate_sql.return_value = "SELECT * FROM transactions LIMIT 5"
    pipeline.llm_client = mock_llm_cls.return_value

    res2 = pipeline.process_query("last 30 days")
    assert res2["status"] == "success"
    assert res2["sql"] == "SELECT * FROM transactions LIMIT 5"
    assert pipeline.pending_clarification_query is None


@patch("localquery.orchestration.pipeline.LocalLLMClient")
def test_pipeline_direct_success(mock_llm_cls):
    """Test a query that doesn't need clarification goes straight through."""
    pipeline = LocalQueryPipeline(db_path=_TEST_DB)
    pipeline.llm_client = MagicMock()
    pipeline.llm_client.generate_sql.return_value = "SELECT * FROM users"

    res = pipeline.process_query("List all users")
    assert res["status"] == "success"
    assert res["sql"] == "SELECT * FROM users"
    assert res["data"]["error"] is None


@patch("localquery.orchestration.pipeline.LocalLLMClient")
def test_pipeline_llm_error_handling(mock_llm_cls):
    """Test that LLM connection errors propagate as error status."""
    pipeline = LocalQueryPipeline(db_path=_TEST_DB)
    pipeline.llm_client = MagicMock()
    pipeline.llm_client.generate_sql.return_value = "Error connecting to Ollama: connection refused"

    res = pipeline.process_query("What is the total balance?")
    assert res["status"] == "error"
    assert "Error" in res["error"]


@patch("localquery.orchestration.pipeline.LocalLLMClient")
def test_pipeline_bad_sql_handling(mock_llm_cls):
    """Test that invalid SQL from the LLM is caught and returned as an error."""
    pipeline = LocalQueryPipeline(db_path=_TEST_DB)
    pipeline.llm_client = MagicMock()
    pipeline.llm_client.generate_sql.return_value = "SELECT * FROM nonexistent_table_xyz"

    res = pipeline.process_query("Show me data")
    assert res["status"] == "error"
    assert res["error"] is not None


@patch("localquery.orchestration.pipeline.LocalLLMClient")
def test_pipeline_result_formatting(mock_llm_cls):
    """Test that the result is returned with a formatted markdown table."""
    pipeline = LocalQueryPipeline(db_path=_TEST_DB)
    pipeline.llm_client = MagicMock()
    pipeline.llm_client.generate_sql.return_value = (
        "SELECT first_name, last_name FROM users LIMIT 2"
    )

    res = pipeline.process_query("Show me some users")
    assert res["status"] == "success"
    assert res["formatted_result"] is not None
    assert "|" in res["formatted_result"]
    assert "first_name" in res["formatted_result"]
