"""Lightweight NLP utilities for ATS scoring.

This module intentionally avoids heavyweight dependencies so it can run in
constrained environments. It provides:
- Tokenization
- Simple lemmatization/stemming heuristics
- Phrase detection for common multi-word terms
- Synonym/alias expansion
- Basic cosine similarity on token frequency vectors
- Importance weighting for job-description keywords
"""

from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Iterable, Sequence


STOPWORDS = {
    "the", "and", "for", "are", "but", "not", "you", "all", "can", "had", "her", "was",
    "one", "our", "out", "has", "have", "been", "were", "will", "with", "this", "that",
    "from", "they", "what", "about", "which", "when", "make", "like", "time", "very",
    "just", "know", "take", "into", "year", "your", "good", "some", "them", "would",
    "there", "their", "should", "work", "also", "more", "other", "than", "then", "these",
    "could", "may", "might", "must", "need", "require", "preferred", "strong", "role",
    "experience", "skills", "responsibilities", "job", "candidate", "least", "minimum",
    "including", "across", "within", "per", "in", "on", "off", "onto", "into", "ensure",
    "ensuring", "ability", "abilities", "capability", "capabilities", "prioritize",
    "prioritise", "prioritizing", "prioritising", "focus", "focusing",
}

# Extra noise terms that often appear in JDs but are not helpful for matching.
NOISE_TERMS = {
    "support", "supporting", "deliver", "delivering", "delivery", "drive", "driving",
    "collaborate", "collaborating", "collaboration", "partner", "partnering",
    "responsible", "responsibility", "responsibilities", "manage", "managed", "managing",
    "lead", "leading", "led", "help", "helping", "assist", "assisting", "assistants",
    "working", "passion", "passionate", "great", "excellent", "best", "success",
}


COMMON_PHRASES = {
    "machine learning",
    "deep learning",
    "data science",
    "data engineering",
    "data analysis",
    "project management",
    "product management",
    "people management",
    "natural language processing",
    "computer vision",
    "continuous integration",
    "continuous delivery",
    "continuous deployment",
    "micro services",
    "microservices",
    "cloud computing",
    "customer success",
    "user experience",
    "user interface",
    "business intelligence",
    "quality assurance",
}


SYNONYM_MAP = {
    "ml": "machine learning",
    "ai": "artificial intelligence",
    "nlp": "natural language processing",
    "cv": "computer vision",
    "pm": "project management",
    "po": "product owner",
    "fe": "frontend",
    "be": "backend",
    "fullstack": "full stack",
    "full-stack": "full stack",
    "javascript": "js",
    "typescript": "ts",
    "postgres": "postgresql",
    "mongo": "mongodb",
    "k8s": "kubernetes",
    "ci": "continuous integration",
    "cd": "continuous delivery",
    "ux": "user experience",
    "ui": "user interface",
    "bi": "business intelligence",
}


TOKEN_PATTERN = re.compile(r"[a-zA-Z][a-zA-Z0-9+\-#.]*")


@dataclass
class NLPDoc:
    """Normalized text representation."""

    tokens: list[str]
    lemmas: list[str]
    phrases: list[str]
    vector: Counter

    def all_terms(self) -> set[str]:
        return set(self.tokens) | set(self.lemmas) | set(self.phrases)


class NLPProcessor:
    """Lightweight NLP helper used across ATS scoring."""

    def __init__(
        self,
        phrases: Sequence[str] | None = None,
        synonym_map: dict[str, str] | None = None,
    ) -> None:
        self.phrases = set(p.lower() for p in (phrases or COMMON_PHRASES))
        self.synonym_map = {k.lower(): v.lower() for k, v in (synonym_map or SYNONYM_MAP).items()}

    def process(self, text: str) -> NLPDoc:
        tokens = self._tokenize(text)
        lemmas = [self._lemmatize(t) for t in tokens]

        # Phrase detection on lemmas for stability
        phrases = self._extract_phrases(lemmas)

        expanded = list(tokens)
        for t in tokens:
            alias = self.synonym_map.get(t)
            if alias:
                expanded.extend(alias.split())

        vector = Counter(lemmas + phrases + expanded)
        return NLPDoc(tokens=tokens, lemmas=lemmas, phrases=phrases, vector=vector)

    def _tokenize(self, text: str) -> list[str]:
        raw_tokens = TOKEN_PATTERN.findall(text.lower())
        return [t for t in raw_tokens if t not in STOPWORDS]

    def _lemmatize(self, token: str) -> str:
        # Very small heuristic lemmatizer good enough for keyword matching.
        if len(token) <= 3:
            return token

        if token.endswith("ies") and len(token) > 4:
            return token[:-3] + "y"
        if token.endswith("sses"):
            return token[:-2]
        if token.endswith("es") and len(token) > 3:
            return token[:-2]
        if token.endswith("s") and len(token) > 3 and not token.endswith("ss"):
            return token[:-1]
        if token.endswith("ing") and len(token) > 5:
            return token[:-3]
        if token.endswith("ed") and len(token) > 4:
            return token[:-2]
        return token

    def _extract_phrases(self, tokens: Sequence[str]) -> list[str]:
        phrases: list[str] = []
        joined = " ".join(tokens)
        for phrase in self.phrases:
            if phrase in joined:
                phrases.append(phrase)
        return phrases

    def filter_signal_terms(self, terms: Iterable[str]) -> set[str]:
        """
        Remove stopwords and high-noise verbs/adjectives so we only surface
        meaningful keywords to users (closer to production-grade ATS filters).
        """
        signal = set()
        for term in terms:
            if len(term) < 3:
                continue
            if term in STOPWORDS or term in NOISE_TERMS:
                continue
            signal.add(term)
        return signal

    def cosine_similarity(self, a: Counter, b: Counter) -> float:
        if not a or not b:
            return 0.0

        dot = sum(a[k] * b.get(k, 0) for k in a)
        norm_a = math.sqrt(sum(v * v for v in a.values()))
        norm_b = math.sqrt(sum(v * v for v in b.values()))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def importance_weights(self, jd_text: str, jd_tokens: Iterable[str]) -> dict[str, float]:
        """
        Assign weights to job description tokens. Tokens near "must/required"
        sentences get higher weight.
        """
        weights = defaultdict(lambda: 1.0)
        sentences = re.split(r"[.!?\n]", jd_text.lower())

        for sentence in sentences:
            if not sentence.strip():
                continue
            sentence_tokens = set(self._tokenize(sentence))
            multiplier = 1.0
            if any(flag in sentence for flag in ["must", "required", "need to", "at least"]):
                multiplier = 1.6
            elif any(flag in sentence for flag in ["preferred", "nice to have", "plus"]):
                multiplier = 1.2
            for tok in sentence_tokens:
                weights[tok] = max(weights[tok], multiplier)

        # Ensure all JD tokens have at least baseline weight
        for tok in jd_tokens:
            weights[tok] = max(weights[tok], 1.0)
        return dict(weights)
