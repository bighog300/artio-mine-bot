from __future__ import annotations

import hashlib
import math
import re
from typing import Iterable


TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9]+")
EMBEDDING_DIMENSIONS = 96


def _tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_PATTERN.findall(text)]


def _bucket_for_token(token: str) -> int:
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % EMBEDDING_DIMENSIONS


def create_embedding(text: str) -> list[float]:
    if not text.strip():
        return [0.0] * EMBEDDING_DIMENSIONS

    vector = [0.0] * EMBEDDING_DIMENSIONS
    for token in _tokenize(text):
        vector[_bucket_for_token(token)] += 1.0

    norm = math.sqrt(sum(value * value for value in vector))
    if norm <= 0:
        return vector

    return [round(value / norm, 6) for value in vector]


def cosine_similarity(left: Iterable[float], right: Iterable[float]) -> float:
    left_list = list(left)
    right_list = list(right)
    if len(left_list) != len(right_list) or not left_list:
        return 0.0

    dot = sum(a * b for a, b in zip(left_list, right_list, strict=True))
    left_norm = math.sqrt(sum(a * a for a in left_list))
    right_norm = math.sqrt(sum(b * b for b in right_list))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)
