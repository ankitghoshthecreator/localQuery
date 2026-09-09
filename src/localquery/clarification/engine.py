import re
from typing import Optional

class ClarificationEngine:
    def __init__(self):
        # Dictionary of heuristic triggers
        self.heuristics = [
            self._check_ambiguous_time,
            self._check_ambiguous_money,
            self._check_ambiguous_status
        ]
        
    def needs_clarification(self, query: str) -> Optional[str]:
        """
        Checks the query against all heuristics.
        Returns a clarification question if ambiguity is found, else None.
        """
        query_lower = query.lower()
        
        for heuristic in self.heuristics:
            question = heuristic(query_lower)
            if question:
                return question
                
        return None

    def _check_ambiguous_time(self, query: str) -> Optional[str]:
        # Missing year for months, or relative terms like 'recent'
        if re.search(r'\b(recent|lately)\b', query):
            return "By 'recent', do you mean the last 30 days, or a different time period?"
        
        if re.search(r'\b(last year)\b', query):
             return "For 'last year', do you mean the previous calendar year (Jan-Dec) or the trailing 12 months?"
             
        if re.search(r'\b(last quarter)\b', query):
             return "Do you mean the calendar quarter (e.g. Q1, Q2) or the trailing 3 months?"
        return None

    def _check_ambiguous_money(self, query: str) -> Optional[str]:
        if re.search(r'\b(revenue|income|money made)\b', query):
            return "When you say 'revenue/income', are you looking for the gross total, or the net after expenses?"
        return None
        
    def _check_ambiguous_status(self, query: str) -> Optional[str]:
        if re.search(r'\b(active users?)\b', query):
            return "For 'active users', do you mean users whose status is 'active' in the database, or users who had a transaction recently?"
        return None
