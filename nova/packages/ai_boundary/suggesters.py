from abc import ABC, abstractmethod
from typing import Any, List
from .models import Suggestion

class Suggester(ABC):
    @abstractmethod
    def suggest(self, raw_input: Any) -> List[Suggestion]:
        """
        Produce suggestions strictly without mutating system state or calling system boundaries directly.
        """
        pass

class MockEntitySuggester(Suggester):
    """
    Given a raw text string, proposes entity suggestions for capitalized words > 2 chars.
    """
    def suggest(self, raw_input: str) -> List[Suggestion]:
        if not isinstance(raw_input, str):
            return []
            
        words = raw_input.split()
        suggestions = []
        for word in words:
            # Strip simple punctuation for mock evaluation
            clean_word = "".join(c for c in word if c.isalpha())
            if len(clean_word) > 2 and clean_word[0].isupper():
                payload = {"name": clean_word}
                sug = Suggestion(
                    suggestion_type="entity",
                    payload=payload,
                    confidence=0.6,
                    source="MockEntitySuggester"
                )
                suggestions.append(sug)
                
        return suggestions

class MockRelationshipSuggester(Suggester):
    def suggest(self, entities: tuple[str, str]) -> List[Suggestion]:
        e1, e2 = entities
        payload = {"source": e1, "target": e2, "relation": "co-occurs-with"}
        sug = Suggestion(
            suggestion_type="relationship",
            payload=payload,
            confidence=0.5,
            source="MockRelationshipSuggester"
        )
        return [sug]
