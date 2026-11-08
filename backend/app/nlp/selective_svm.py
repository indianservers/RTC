"""Pickle-stable selective text SVM; ML packages are required only by loaded estimators."""

from math import isfinite


def decide(scores, domain_margin, classes, thresholds):
    if len(scores) != len(classes) or len(scores) < 2:
        raise ValueError("Multiclass scores and labels must agree")
    numbers = [float(x) for x in scores]
    domain_margin = float(domain_margin)
    if not all(isfinite(x) for x in numbers + [domain_margin]):
        raise ValueError("Non-finite inference scores")
    ranked = sorted(range(len(numbers)), key=lambda i: (-numbers[i], str(classes[i])))
    top, second = ranked[:2]
    margin, gap = numbers[top], numbers[top] - numbers[second]
    status = "KNOWN"
    if domain_margin < thresholds["domain"]:
        status = "OUT_OF_SCOPE"
    elif margin < thresholds["margin"] or gap < thresholds["gap"]:
        status = "CLARIFICATION_REQUIRED"
    return {
        "status": status,
        "intents": [str(classes[top])] if status == "KNOWN" else [],
        "decision_margin": margin,
        "domain_margin": domain_margin,
        "top_two_gap": gap,
        "threshold_source": "validation",
        "probability": None,
    }


class SelectiveIntentSVM:
    def __init__(self, features, intent_model, domain_model, thresholds):
        self.features = features
        self.intent_model = intent_model
        self.domain_model = domain_model
        self.thresholds = dict(thresholds)
        self.classes_ = intent_model.classes_

    def predict(self, texts):
        """Forced-choice diagnostic only. Use predict_selective to obtain rejection."""
        return self.intent_model.predict(self.features.transform(texts))

    def decision_function(self, texts):
        return self.intent_model.decision_function(self.features.transform(texts))

    def predict_selective(self, texts):
        if not all(isinstance(t, str) and 1 <= len(t) <= 2000 for t in texts):
            raise ValueError("Text inputs must contain 1 to 2000 characters")
        vectors = self.features.transform(texts)
        scores = self.intent_model.decision_function(vectors)
        domain = self.domain_model.decision_function(vectors)
        return [
            decide(s, d, self.classes_, self.thresholds)
            for s, d in zip(scores, domain, strict=True)
        ]
