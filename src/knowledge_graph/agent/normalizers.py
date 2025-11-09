"""Small set of value normalizers for mapping-based transforms."""

from __future__ import annotations

import re
from typing import Any, Callable, Dict


def trim(x: Any) -> str:
    s = "" if x is None else str(x)
    return s.strip()


def to_lower(x: Any) -> str:
    return trim(x).lower()


def to_upper(x: Any) -> str:
    return trim(x).upper()


def title_case(x: Any) -> str:
    return trim(x).title()


def slug(x: Any) -> str:
    s = to_lower(x)
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")
    return s


def to_int(x: Any) -> str:
    s = trim(x)
    if s == "":
        return ""
    try:
        return str(int(float(s)))
    except Exception:
        return ""


def to_float(x: Any) -> str:
    s = trim(x)
    if s == "":
        return ""
    try:
        return str(float(s))
    except Exception:
        return ""


def to_bool(x: Any) -> str:
    s = to_lower(x)
    if s in {"true", "t", "yes", "y", "1"}:
        return "true"
    if s in {"false", "f", "no", "n", "0"}:
        return "false"
    return ""


REGISTRY: Dict[str, Callable[[Any], str]] = {
    "trim": trim,
    "lower": to_lower,
    "upper": to_upper,
    "title_case": title_case,
    "slug": slug,
    "to_int": to_int,
    "to_float": to_float,
    "to_bool": to_bool,
    "identity": lambda x: "" if x is None else str(x),
}


__all__ = [
    "REGISTRY",
    "trim",
    "to_lower",
    "to_upper",
    "title_case",
    "slug",
    "to_int",
    "to_float",
    "to_bool",
]

