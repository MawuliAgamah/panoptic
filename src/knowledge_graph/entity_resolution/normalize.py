from __future__ import annotations

import re
import unicodedata


_PUNCT_RE = re.compile(r"[^a-z0-9\s]")
_WS_RE = re.compile(r"\s+")


def _basic_normalize(text: str) -> str:
    t = text or ""
    t = unicodedata.normalize("NFKD", t)
    t = t.encode("ascii", "ignore").decode("ascii")  # strip diacritics
    t = t.lower().strip()
    t = _PUNCT_RE.sub(" ", t)
    t = _WS_RE.sub(" ", t).strip()
    return t


def _normalize_person(name: str) -> str:
    t = _basic_normalize(name)
    # Drop common honorifics and middle initials
    t = re.sub(r"\b(dr|prof|mr|mrs|ms)\b\.?:?\s*", "", t)
    t = re.sub(r"\b([a-z])\.\b", r"\1", t)  # remove middle initials like "y."
    # Reorder "last, first" to "first last"
    if "," in t:
        parts = [p.strip() for p in t.split(",")]
        if len(parts) == 2:
            t = f"{parts[1]} {parts[0]}"
    t = _WS_RE.sub(" ", t)
    return t.strip()


def _normalize_org(name: str) -> str:
    t = _basic_normalize(name)
    t = t.replace("&", " and ")
    # Drop common suffixes
    t = re.sub(r"\b(inc|ltd|corp|llc|co)\b", "", t)
    t = _WS_RE.sub(" ", t)
    return t.strip()


def _normalize_location(name: str) -> str:
    t = _basic_normalize(name)
    # Expand a couple of common abbreviations
    t = re.sub(r"\bst\.?\b", "street", t)
    t = re.sub(r"\bave\.?\b", "avenue", t)
    t = _WS_RE.sub(" ", t)
    return t.strip()


def normalize_name(name: str, ent_type: str) -> str:
    """Normalize an entity name into a canonical form for exact matching.

    ent_type is used only for light type-aware tweaks; defaults to basic normalization.
    """
    et = (ent_type or "").lower().strip()
    if et in {"person", "people", "author"}:
        return _normalize_person(name)
    if et in {"org", "organization", "company", "institution"}:
        return _normalize_org(name)
    if et in {"location", "place", "city"}:
        return _normalize_location(name)
    return _basic_normalize(name)

