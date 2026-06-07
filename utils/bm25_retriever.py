from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from typing import Any, Dict, Iterable, List


def normalize_text(value: Any) -> str:
    return unicodedata.normalize("NFKC", str(value or "")).lower()


def tokenize(value: Any) -> List[str]:
    text = normalize_text(value)
    tokens = re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]", text)
    grams: List[str] = []

    for token in tokens:
        if re.fullmatch(r"[a-z0-9]+", token):
            grams.append(token)

    chinese_chars = [token for token in tokens if re.fullmatch(r"[\u4e00-\u9fff]", token)]
    grams.extend(chinese_chars)
    grams.extend("".join(chinese_chars[idx : idx + 2]) for idx in range(max(len(chinese_chars) - 1, 0)))
    grams.extend("".join(chinese_chars[idx : idx + 3]) for idx in range(max(len(chinese_chars) - 2, 0)))
    return [token for token in dict.fromkeys(grams) if token]


class BM25Retriever:
    def __init__(self, chunks: List[Dict[str, Any]], *, k1: float = 1.5, b: float = 0.75):
        self.chunks = chunks
        self.k1 = k1
        self.b = b
        self.doc_tokens: List[List[str]] = [tokenize(chunk.get("text", "")) for chunk in chunks]
        self.doc_lengths = [len(tokens) for tokens in self.doc_tokens]
        self.avg_doc_length = sum(self.doc_lengths) / max(len(self.doc_lengths), 1)
        self.doc_freq = self._build_doc_freq(self.doc_tokens)

    @staticmethod
    def _build_doc_freq(docs: Iterable[List[str]]) -> Counter:
        doc_freq = Counter()
        for tokens in docs:
            doc_freq.update(set(tokens))
        return doc_freq

    def _score_doc(self, query_tokens: List[str], doc_index: int) -> float:
        term_counts = Counter(self.doc_tokens[doc_index])
        doc_length = self.doc_lengths[doc_index] or 1
        total_docs = max(len(self.chunks), 1)
        score = 0.0

        for term in query_tokens:
            tf = term_counts.get(term, 0)
            if not tf:
                continue
            df = self.doc_freq.get(term, 0)
            idf = math.log((total_docs - df + 0.5) / (df + 0.5) + 1.0)
            denominator = tf + self.k1 * (1 - self.b + self.b * doc_length / max(self.avg_doc_length, 1))
            score += idf * (tf * (self.k1 + 1)) / denominator

        return score

    def search(self, query: str, *, top_k: int = 8) -> List[Dict[str, Any]]:
        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        results = []
        for idx, chunk in enumerate(self.chunks):
            score = self._score_doc(query_tokens, idx)
            if score <= 0:
                continue
            results.append(
                {
                    **chunk,
                    "bm25_score": round(score, 6),
                    "retriever": "bm25",
                }
            )

        results.sort(key=lambda item: item["bm25_score"], reverse=True)
        return results[:top_k]
