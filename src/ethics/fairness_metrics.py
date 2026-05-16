import json
import os

class FairnessEvaluator:
    def __init__(self, bias_lexicon_path: str = "config/bias_lexicon.json"):
        self._bias_terms: set[str] = set()
        
        # Safely load the bias lexicon
        if os.path.exists(bias_lexicon_path):
            with open(bias_lexicon_path, "r") as f:
                raw = json.load(f)
            
            for key, terms in raw.items():
                if key == "bias_lexicon_metadata":
                    continue
                for term in terms:
                    clean = term.split(" (")[0].lower()
                    self._bias_terms.add(clean)

    def evaluate_fairness(self, text: str) -> dict:
        """
        Checks for terms that violate the fairness and human-centric RAI principles.
        """
        lower = text.lower()
        for term in self._bias_terms:
            if term in lower:
                return {
                    "is_fair": False,
                    "bias_term": term,
                    "fairness_score": 0.0,
                    "reason": f"Potential fairness or bias concern detected related to: '{term}'"
                }
        return {
            "is_fair": True,
            "bias_term": None,
            "fairness_score": 1.0,
            "reason": "Passed fairness checks."
        }

# Global singleton for use
_evaluator = None

def get_fairness_evaluator() -> FairnessEvaluator:
    global _evaluator
    if _evaluator is None:
        _evaluator = FairnessEvaluator()
    return _evaluator
