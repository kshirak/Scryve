"""Text normalization and lightweight tokenization helpers."""

from __future__ import annotations

import re
from typing import Iterable

_WHITESPACE_RE = re.compile(r"\s+")
_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9+.#/-]*")


def clean_whitespace(value: str) -> str:
    """Collapse internal whitespace runs into single spaces and strip ends.

    Args:
        value: Raw string.

    Returns:
        Whitespace-normalized string.
    """
    return _WHITESPACE_RE.sub(" ", value).strip()


def normalize_text(value: str) -> str:
    """Lower-case + whitespace-normalize a string for case-insensitive ops.

    Args:
        value: Raw string.

    Returns:
        Lower-cased, whitespace-normalized string.
    """
    return clean_whitespace(value.lower())


def tokenize(value: str) -> list[str]:
    """Tokenize a string into lower-case alphanumeric+ tokens.

    Preserves common technical punctuation (`+`, `.`, `#`, `/`, `-`) so
    tokens like ``c++``, ``a/b``, ``tf.idf``, and ``c#`` survive intact.

    Args:
        value: Raw string.

    Returns:
        List of token strings.
    """
    return _TOKEN_RE.findall(value.lower())


def contains_any(haystack: str, needles: Iterable[str]) -> list[str]:
    """Return which `needles` appear as substrings of `haystack`.

    Comparison is case-insensitive. Useful for keyword spotting in
    candidate descriptions and JD bullets.

    Args:
        haystack: The text to search.
        needles: Candidate substrings to look for.

    Returns:
        The subset of `needles` that occur in `haystack`.
    """
    normalized = haystack.lower()
    return [n for n in needles if n.lower() in normalized]
