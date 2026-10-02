import pytest
from localquery.clarification.engine import ClarificationEngine


@pytest.fixture
def engine():
    return ClarificationEngine()


# ---------------------------------------------------------------------------
# Time heuristics
# ---------------------------------------------------------------------------
def test_time_heuristics_recent(engine):
    assert engine.needs_clarification("Show recent transactions") is not None
    assert "recent" in engine.needs_clarification("Show recent transactions").lower() or \
           "30 days" in engine.needs_clarification("Show recent transactions")


def test_time_heuristics_lately(engine):
    assert engine.needs_clarification("What has happened lately?") is not None


def test_time_heuristics_last_year(engine):
    assert engine.needs_clarification("What was the revenue last year?") is not None


def test_time_heuristics_last_quarter(engine):
    assert engine.needs_clarification("Show sales for last quarter") is not None


def test_time_heuristics_no_trigger(engine):
    assert engine.needs_clarification("Show users signed up in 2023") is None
    assert engine.needs_clarification("Get transactions from January 2024") is None


# ---------------------------------------------------------------------------
# Money heuristics
# ---------------------------------------------------------------------------
def test_money_heuristics_revenue(engine):
    result = engine.needs_clarification("How much revenue did we generate?")
    assert result is not None
    assert "gross" in result.lower() or "net" in result.lower()


def test_money_heuristics_income(engine):
    assert engine.needs_clarification("What is our total income?") is not None


def test_money_heuristics_no_trigger(engine):
    assert engine.needs_clarification("Show total balance in savings") is None
    assert engine.needs_clarification("What is Alice's account balance?") is None


# ---------------------------------------------------------------------------
# Status heuristics
# ---------------------------------------------------------------------------
def test_status_heuristics_active_users(engine):
    result = engine.needs_clarification("List all active users")
    assert result is not None


def test_status_heuristics_active_user_singular(engine):
    assert engine.needs_clarification("Show active user count") is not None


def test_status_heuristics_no_trigger(engine):
    assert engine.needs_clarification("Show users with status active") is None
    assert engine.needs_clarification("Find inactive users") is None


# ---------------------------------------------------------------------------
# Ranking heuristics
# ---------------------------------------------------------------------------
def test_ranking_heuristics_top_users(engine):
    assert engine.needs_clarification("Show the top users") is not None


def test_ranking_heuristics_best_customers(engine):
    assert engine.needs_clarification("Who are our best customers?") is not None


def test_ranking_heuristics_top_accounts(engine):
    assert engine.needs_clarification("Show the top 5 accounts") is not None


# ---------------------------------------------------------------------------
# Custom heuristic extensibility
# ---------------------------------------------------------------------------
def test_custom_heuristic(engine):
    engine.add_heuristic(lambda q: "Custom question?" if "secret" in q else None)
    assert engine.needs_clarification("What is the secret query?") == "Custom question?"


def test_custom_heuristic_does_not_affect_others(engine):
    engine.add_heuristic(lambda q: "Custom question?" if "secret" in q else None)
    # Still returns None for unambiguous queries
    assert engine.needs_clarification("Show all users") is None


def test_multiple_custom_heuristics(engine):
    engine.add_heuristic(lambda q: "Q1?" if "foo" in q else None)
    engine.add_heuristic(lambda q: "Q2?" if "bar" in q else None)
    # First matching heuristic wins
    assert engine.needs_clarification("foo bar query") == "Q1?"


# ---------------------------------------------------------------------------
# Short-circuit (first match wins)
# ---------------------------------------------------------------------------
def test_first_heuristic_wins(engine):
    """When multiple heuristics fire, the first one is returned."""
    # 'revenue' triggers money AND could be in a 'recent revenue' query
    result = engine.needs_clarification("Show recent revenue")
    assert result is not None
    # Should be the time heuristic (first registered) 
    assert "recent" in result.lower() or "30 days" in result.lower()
