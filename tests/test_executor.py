import os
import sqlite3
import pytest
from localquery.db.executor import DBExecutor
from localquery.db.schema import setup_db

# Use a fixed path inside the project that the sandbox can write to
_TEST_DB = os.path.join(os.path.dirname(__file__), "_test_executor.db")


@pytest.fixture(autouse=True)
def temp_db():
    """Set up and tear down a test database in the tests directory."""
    if os.path.exists(_TEST_DB):
        os.remove(_TEST_DB)
    setup_db(_TEST_DB)
    yield _TEST_DB
    if os.path.exists(_TEST_DB):
        try:
            os.remove(_TEST_DB)
        except OSError:
            pass


def test_select_query_execution():
    executor = DBExecutor(db_path=_TEST_DB)
    res = executor.execute_query("SELECT first_name, status FROM users LIMIT 2")
    assert res["error"] is None
    assert "first_name" in res["columns"]
    assert len(res["rows"]) == 2


def test_non_select_query_rejection():
    executor = DBExecutor(db_path=_TEST_DB)
    res = executor.execute_query("DROP TABLE users")
    assert res["error"] == "Only SELECT queries are allowed."


def test_format_results():
    executor = DBExecutor(db_path=_TEST_DB)
    res = executor.execute_query("SELECT user_id, email FROM users LIMIT 1")
    formatted = executor.format_results(res)
    assert "|" in formatted
    assert "user_id" in formatted


def test_invalid_sql_syntax():
    executor = DBExecutor(db_path=_TEST_DB)
    res = executor.execute_query("SELECT * FROM non_existent_table")
    assert res["error"] is not None


def test_empty_result_set():
    """Test formatting when no rows are returned."""
    executor = DBExecutor(db_path=_TEST_DB)
    # inactive users may or may not exist, but force an empty via impossible condition
    res = executor.execute_query("SELECT * FROM users WHERE 1=0")
    assert res["error"] is None
    assert res["rows"] == []
    formatted = executor.format_results(res)
    assert formatted == "No results found."


def test_aggregation_query():
    executor = DBExecutor(db_path=_TEST_DB)
    res = executor.execute_query("SELECT COUNT(*) AS total_users FROM users")
    assert res["error"] is None
    assert "total_users" in res["columns"]
    assert res["rows"][0][0] >= 1


def test_join_query():
    executor = DBExecutor(db_path=_TEST_DB)
    sql = ("SELECT u.first_name, a.account_type, a.balance "
           "FROM users u JOIN accounts a ON u.user_id = a.user_id "
           "LIMIT 3")
    res = executor.execute_query(sql)
    assert res["error"] is None
    assert "first_name" in res["columns"]
    assert "balance" in res["columns"]
