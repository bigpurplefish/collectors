"""
Text matching utilities for Ethical Products collector.

Provides product name normalization and matching logic.
"""

import re
from typing import Dict, List, Set

# Regex patterns
_WS = re.compile(r"\s+")
_NON_ALNUM = re.compile(r"[^A-Za-z0-9]+")
_MFR_WORDS = re.compile(r"\b(?:ETHICAL(?:\s+PRODUCTS?)?|SPOT)\b", re.I)
_QTY_WORDS = re.compile(r"\b(?:COUNT|CT|PACK|PK|BULK|ASSTD|ASST|ASSORTED|EACH|EA|SET|BX|BOX|PDQ|DISPLAY|CASE)\b", re.I)
_SIZE_WORDS = re.compile(r"\b(?:OZ|OUNCES?|LB|LBS?|POUNDS?|G|GRAMS?|KG|MLS?|ML|L|LITERS?|QT|QTS?|QUARTS?|GALS?|GAL|IN|INCH(?:ES)?)\b", re.I)
_CAT_HINT = re.compile(r"\b(?:CAT|KITTY|KITTEN|LITTER)\b", re.I)
_DOG_HINT = re.compile(r"\b(?:DOG|PUP|PUPPY|CANINE)\b", re.I)
_DISH_HINT = re.compile(r"\b(?:BOWL|DISH|FEEDER|STONEWARE|CERAMIC)\b", re.I)

# Canonical mappings
FLAVOR_CANON = {
    "PEANUT BUTTER": {"PEANUT", "PEANUTBUTTER", "PB", "PEANUT-BUTTER", "PEANUT_BUTTER"},
    "BACON": {"BACON"},
    "APPLE": {"APPLE"},
    "GINGERBREAD": {"GINGERBREAD"},
}

LINE_CANON = {
    "PLAY STRONG": {"PLAYSTRONG", "PLAY-STRONG", "FOAMZ", "SCENT-SATION", "SCENTSATION"},
    "BARRETT": {"BARRETT"},
    "BAMBONE": {"BAMBONE", "BAM-BONE", "BAM BONE"},
    "SKINNEEEZ": {"SKINNEEEZ", "SKINEEZ", "SKINNEEZ"},
}

FORM_TOKENS = {
    "BALL", "BONE", "TRIPOD", "X-BONE", "XBONE", "WISHBONE", "DINO", "RING",
    "DISH", "BOWL", "FEEDER", "BRIDGE", "CHEW", "TUG", "STICK",
}


def normalize_name(raw: str) -> str:
    """
    Normalize product name for matching.

    Removes manufacturer names, size/quantity words, common stopwords.

    Args:
        raw: Raw product name

    Returns:
        Normalized name in uppercase
    """
    s = _WS.sub(" ", raw.strip())
    s = _MFR_WORDS.sub(" ", s)
    s = s.replace("-", "")
    s = _QTY_WORDS.sub(" ", s)
    s = _SIZE_WORDS.sub(" ", s)
    s = re.sub(
        r'\b(?:WITH|W/|W|AND|&|THE|FOR|OF|TO|PLUS|EXTRA|NEW|OR)\b',
        " ",
        s,
        flags=re.I
    )
    s = re.sub(r'[/"""''()+,]', " ", s)
    s = _WS.sub(" ", s).strip().upper()

    parts = s.split()
    if parts:
        parts[0] = singularize_simple(parts[0])

    return " ".join(parts)


def singularize_simple(tok: str) -> str:
    """
    Simple singularization of token.

    Args:
        tok: Token to singularize

    Returns:
        Singularized token
    """
    if tok.endswith("IES") and len(tok) > 3:
        return tok[:-3] + "Y"
    if tok.endswith("S") and not tok.endswith("SS"):
        return tok[:-1]
    return tok


def extract_canonical_flavors(text: str) -> Set[str]:
    """
    Extract canonical flavor names from text.

    Args:
        text: Text to search for flavors

    Returns:
        Set of canonical flavor names
    """
    u = (text or "").upper().replace("-", " ").replace("_", " ")
    toks = set(_NON_ALNUM.split(u))
    out = set()

    for canon, alts in FLAVOR_CANON.items():
        if canon in u or alts.intersection(toks):
            out.add(canon)

    return out


def extract_canonical_line(text: str) -> Set[str]:
    """
    Extract canonical product line names from text.

    Args:
        text: Text to search for lines

    Returns:
        Set of canonical line names
    """
    u = (text or "").upper().replace("-", "")
    toks = set(text.split())
    out = set()

    for canon, alts in LINE_CANON.items():
        if canon in u or alts.intersection(toks):
            out.add(canon)

    return out


def extract_form_tokens(text: str) -> Set[str]:
    """
    Extract product form tokens (ball, bone, etc.).

    Args:
        text: Text to search

    Returns:
        Set of form tokens found
    """
    toks = set(text.upper().split())
    if "XBONE" in toks:
        toks.add("X-BONE")
    return {t for t in toks if t in FORM_TOKENS}


def infer_taxonomy(text: str) -> str:
    """
    Infer product taxonomy (cat/dog/dish) from text.

    Args:
        text: Product description or title

    Returns:
        Taxonomy hint: "cat", "dog", "dish", or ""
    """
    if _DISH_HINT.search(text):
        return "dish"
    if _CAT_HINT.search(text):
        return "cat"
    if _DOG_HINT.search(text):
        return "dog"

    # Brand-specific clues
    if re.search(
        r"\bSKINNEEEZ|SKINEEZ|SILVER\s*VINE|KITTY|CATNIP|TEASER|LITTER|FEATHER|FELT\b",
        text,
        re.I
    ):
        return "cat"
    if re.search(r"\bPLAY\s*STRONG|BAMBONE|BARRETT\b", text, re.I):
        return "dog"

    return ""
