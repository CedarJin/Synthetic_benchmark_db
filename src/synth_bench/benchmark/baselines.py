"""Simple baseline methods for ingredient parsing and mapping.

These serve as reference points for evaluating parsing/mapping quality.
They are intentionally simple — not production-grade.
"""

from __future__ import annotations

import re

# ═══════════════════════════════════════════════════════════════════════════════
# Baseline Ingredient Parser
# ═══════════════════════════════════════════════════════════════════════════════


def baseline_parse_ingredients(label_text: str) -> list[str]:
    """Simple regex-based ingredient list parser.

    Handles common patterns:
      - "INGREDIENTS: item1, item2, item3."
      - "Contains 2% or less of: ..."
      - Compound ingredients: "ITEM (sub1, sub2)"
      - "Contains: allergen1, allergen2"

    Args:
        label_text: Full ingredient declaration text.

    Returns:
        List of extracted ingredient names (ordered).
    """
    if not label_text:
        return []

    # Remove "INGREDIENTS:" prefix
    text = re.sub(r"^INGREDIENTS:\s*", "", label_text, flags=re.IGNORECASE)

    # Split on periods that are NOT part of an abbreviation, then rejoin
    # This handles "INGREDIENTS: A, B. CONTAINS 2% OR LESS: C." → "A, B, C"
    text = re.sub(r"\.\s+", ", ", text)

    # Remove "CONTAINS 2% OR LESS OF:" (separate items but still ingredients)
    text = re.sub(r"CONTAINS 2%\s*OR\s*LESS\s*OF:\s*", "", text, flags=re.IGNORECASE)

    # Remove "CONTAINS:" and "CONTAINS " (allergen declarations)
    text = re.sub(r"CONTAINS:?\s*.*?$", "", text, flags=re.IGNORECASE)

    # Remove trailing period
    text = text.strip().rstrip(".")

    if not text:
        return []

    # Split by comma, handling parenthetical sub-ingredients
    ingredients: list[str] = []
    current = ""
    paren_depth = 0
    for char in text:
        if char == "(":
            paren_depth += 1
            current += char
        elif char == ")":
            paren_depth -= 1
            current += char
        elif char == "," and paren_depth == 0:
            ingredients.append(current.strip())
            current = ""
        else:
            current += char
    if current.strip():
        ingredients.append(current.strip())

    # Clean up: remove parenthetical sub-ingredients from display
    cleaned = []
    for ing in ingredients:
        ing = ing.strip().rstrip(".")
        # Remove parenthetical sub-ingredients for display
        paren_idx = ing.find("(")
        if paren_idx > 0:
            ing = ing[:paren_idx].strip()
        if ing:
            cleaned.append(ing)

    return cleaned


# ═══════════════════════════════════════════════════════════════════════════════
# Baseline Ingredient Mapper
# ═══════════════════════════════════════════════════════════════════════════════


def build_ingredient_dictionary(
    known_pairs: dict[str, str] | None = None,
) -> dict[str, str]:
    """Build a simple ingredient dictionary for exact matching.

    Uses the STANDARD_TO_COMMERCIAL mapping from the knowledge base.

    Args:
        known_pairs: Optional custom dictionary. If None, uses built-in.

    Returns:
        {ingredient_name_lower: standard_id}
    """
    from synth_bench.knowledge.ingredient_knowledge import STANDARD_TO_COMMERCIAL

    if known_pairs is not None:
        return {k.lower(): v for k, v in known_pairs.items()}

    # Build reverse mapping: commercial name → standard name
    dictionary: dict[str, str] = {}
    for standard, commercial in STANDARD_TO_COMMERCIAL.items():
        commercial_lower = commercial.lower()
        standard_lower = standard.lower()
        # Map commercial → standard
        dictionary[commercial_lower] = standard
        # Also map standard → standard
        dictionary[standard_lower] = standard

    return dictionary


def baseline_dictionary_mapper(
    ingredient_names: list[str],
    dictionary: dict[str, str] | None = None,
) -> dict[str, list[str]]:
    """Map ingredients to standard IDs using dictionary lookup.

    Args:
        ingredient_names: List of ingredient names to map.
        dictionary: Mapping dict {name_lower: standard_id}.

    Returns:
        {ingredient_name: [ranked_target_ids]}.
    """
    if dictionary is None:
        dictionary = build_ingredient_dictionary()

    results: dict[str, list[str]] = {}
    for name in ingredient_names:
        name_lower = name.lower()
        candidates: list[str] = []

        # Exact match
        if name_lower in dictionary:
            candidates.append(dictionary[name_lower])

        # Word-level partial match
        if not candidates:
            words = set(name_lower.split())
            for dict_key, std_name in dictionary.items():
                dict_words = set(dict_key.split())
                if words & dict_words:  # any word overlap
                    candidates.append(std_name)

        results[name] = candidates[:5]  # top-5
    return results


def baseline_bm25_mapper(
    ingredient_names: list[str],
    dictionary: dict[str, str] | None = None,
) -> dict[str, list[str]]:
    """Simple TF-style mapper (analogous to BM25).

    Scores candidates by shared word count over total unique words.

    Args:
        ingredient_names: List of ingredient names to map.
        dictionary: Mapping dict.

    Returns:
        {ingredient_name: [ranked_target_ids]}.
    """
    if dictionary is None:
        dictionary = build_ingredient_dictionary()

    results: dict[str, list[str]] = {}
    for name in ingredient_names:
        name_lower = name.lower()
        query_words = set(name_lower.split())

        scored: list[tuple[str, float]] = []
        for dict_key, std_name in dictionary.items():
            dict_words = set(dict_key.split())
            if not query_words or not dict_words:
                continue
            overlap = len(query_words & dict_words)
            total = len(query_words | dict_words)
            score = overlap / total if total > 0 else 0.0
            if score > 0:
                scored.append((std_name, score))

        # Sort by score descending
        scored.sort(key=lambda x: x[1], reverse=True)
        results[name] = [s[0] for s in scored[:5]]
    return results
