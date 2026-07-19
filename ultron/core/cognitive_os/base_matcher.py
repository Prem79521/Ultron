"""
ULTRON Cognitive OS — Fuzzy Matcher abstraction and implementations.
"""

import difflib
from typing import List, Tuple

class BaseMatcher:
    """Abstract interface for fuzzy string matching."""
    def ratio(self, str1: str, str2: str) -> float:
        """Returns similarity score between 0.0 and 1.0."""
        raise NotImplementedError

    def get_matches(self, query: str, possibilities: List[str], cutoff: float = 0.6) -> List[Tuple[str, float]]:
        """Returns list of tuples (matched_string, score) sorted by score descending."""
        raise NotImplementedError

class DifflibMatcher(BaseMatcher):
    """Fuzzy matcher using standard library's difflib."""
    def ratio(self, str1: str, str2: str) -> float:
        if not str1 or not str2:
            return 0.0
        return difflib.SequenceMatcher(None, str1.lower().strip(), str2.lower().strip()).ratio()

    def get_matches(self, query: str, possibilities: List[str], cutoff: float = 0.6) -> List[Tuple[str, float]]:
        results = []
        query_clean = query.lower().strip()
        for pos in possibilities:
            score = self.ratio(query_clean, pos)
            if score >= cutoff:
                results.append((pos, score))
        return sorted(results, key=lambda x: x[1], reverse=True)
