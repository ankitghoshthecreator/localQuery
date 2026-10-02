"""
LocalQuery Clarification Engine
=================================
Detects ambiguous natural language queries using a set of heuristic rules
and returns a targeted follow-up question to resolve the ambiguity before
generating SQL.
"""

from __future__ import annotations

import re
from typing import Callable, Optional


class ClarificationEngine:
    """
    Evaluates a user query against registered heuristics and returns a
    clarification question when ambiguity is detected.

    Usage::

        engine = ClarificationEngine()
        question = engine.needs_clarification("Show recent transactions")
        # Returns: "By 'recent', do you mean the last 30 days, or a different time period?"
    """

    def __init__(self):
        # Built-in heuristics — order matters; the first match is returned.
        self.heuristics: list[Callable[[str], Optional[str]]] = [
            self._check_ambiguous_time,
            self._check_ambiguous_money,
            self._check_ambiguous_status,
            self._check_ambiguous_ranking,
            self._check_ambiguous_comparison,
        ]

    def add_heuristic(self, func: Callable[[str], Optional[str]]) -> None:
        """Register a custom clarification heuristic at the end of the chain."""
        self.heuristics.append(func)

    def needs_clarification(self, query: str) -> Optional[str]:
        """
        Run all heuristics against the query in registration order.

        Args:
            query: The raw user query string.

        Returns:
            A clarification question string if ambiguity is detected,
            otherwise None.
        """
        query_lower = query.lower()
        for heuristic in self.heuristics:
            question = heuristic(query_lower)
            if question:
                return question
        return None

    # ------------------------------------------------------------------
    # Built-in heuristic methods
    # ------------------------------------------------------------------

    def _check_ambiguous_time(self, query: str) -> Optional[str]:
        """Catches relative/vague time references."""
        if re.search(r"\b(recent|lately)\b", query):
            return (
                "By 'recent', do you mean the last 30 days, "
                "or a different time period?"
            )
        if re.search(r"\blast\s+year\b", query):
            return (
                "For 'last year', do you mean the previous calendar year "
                "(Jan–Dec) or the trailing 12 months?"
            )
        if re.search(r"\blast\s+quarter\b", query):
            return (
                "Do you mean the calendar quarter (e.g. Q1, Q2) "
                "or the trailing 3 months?"
            )
        if re.search(r"\blast\s+month\b", query):
            return (
                "For 'last month', do you mean the previous calendar month "
                "or the trailing 30 days?"
            )
        if re.search(r"\bthis\s+(year|month|quarter)\b", query):
            return (
                "For 'this year/month/quarter', do you mean the current "
                "calendar period from the 1st, or the rolling period up to today?"
            )
        return None

    def _check_ambiguous_money(self, query: str) -> Optional[str]:
        """Catches gross vs. net revenue / income ambiguity."""
        if re.search(r"\b(revenue|income|money\s+made|earnings)\b", query):
            return (
                "When you say 'revenue/income', are you looking for the "
                "gross total, or the net after expenses?"
            )
        return None

    def _check_ambiguous_status(self, query: str) -> Optional[str]:
        """Catches 'active users' where status field vs. activity could differ."""
        if re.search(r"\bactive\s+users?\b", query):
            return (
                "For 'active users', do you mean users whose status is 'active' "
                "in the database, or users who had a transaction recently?"
            )
        return None

    def _check_ambiguous_ranking(self, query: str) -> Optional[str]:
        """Catches 'top / best' ranking without a defined metric."""
        if re.search(r"\b(top|best)\s+(users?|customers?|accounts?|clients?)\b", query):
            return (
                "By 'top/best', do you mean ranked by highest account balance, "
                "highest transaction volume, or total spend?"
            )
        return None

    def _check_ambiguous_comparison(self, query: str) -> Optional[str]:
        """Catches vague comparison words like 'large', 'high', 'significant'."""
        if re.search(r"\b(large|large-scale|high|significant|big)\b", query):
            if re.search(r"\b(transaction|amount|balance|payment|order)\b", query):
                return (
                    "What threshold defines 'large/high' for you? "
                    "For example, amounts above a certain value (e.g. $1,000)?"
                )
        return None
