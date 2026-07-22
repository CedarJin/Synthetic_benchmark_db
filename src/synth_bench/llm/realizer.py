"""Label Realizer — renders StructuredLabel to commercial label text.

Provides:
  1. Template-based deterministic rendering (always available).
  2. Optional LLM-based refinement for more natural language.

The LLM is strictly constrained: it may only rewrite the language,
never add/remove/reorder ingredients or alter regulatory statements.
"""

from __future__ import annotations

from synth_bench.canonical.models import (
    BenchmarkSample,
    NutritionFactsPanel,
    StructuredLabel,
)

# ═══════════════════════════════════════════════════════════════════════════════
# Template-based Label Realizer
# ═══════════════════════════════════════════════════════════════════════════════


def _render_ingredient_list(label: StructuredLabel) -> str:
    """Render the ingredient list as commercial label text.

    Follows FDA format conventions:
      - Main ingredients in descending order (by original fraction).
      - Compound ingredients shown as "PARENT INGREDIENT (sub1, sub2, ...)".
      - ≤2% group appended as "Contains 2% or less of: item1, item2".
      - Allergen declarations appended separately.

    Args:
        label: Structured label to render.

    Returns:
        Formatted ingredient declaration string.
    """
    parts: list[str] = []

    # Main ingredient list
    main_texts: list[str] = []
    for ing in label.ingredient_list:
        name = ing.declared_name
        main_texts.append(name)

    if main_texts:
        parts.append(", ".join(main_texts))

    # ≤2% group
    if label.two_percent_group:
        lt_texts = [ing.declared_name for ing in label.two_percent_group]
        parts.append(f"CONTAINS 2% OR LESS OF: {', '.join(lt_texts)}")

    # Allergen declaration
    if label.allergens is not None:
        parts.append(label.allergens.declaration_text)

    full_text = ", ".join(parts)

    # Ensure proper casing: "INGREDIENTS: ..."
    if not full_text.startswith("INGREDIENTS"):
        full_text = f"INGREDIENTS: {full_text}."

    return full_text


def _render_nutrition_facts(nf: NutritionFactsPanel) -> str:
    """Render Nutrition Facts panel as text.

    Args:
        nf: Nutrition Facts panel data.

    Returns:
        Formatted Nutrition Facts text block.
    """
    lines: list[str] = [
        "Nutrition Facts",
        f"Serving Size {nf.serving_size}",
    ]
    if nf.servings_per_container:
        lines.append(f"Servings Per Container {nf.servings_per_container}")

    # Separator
    lines.append("")

    # Calories
    lines.append(f"Calories {nf.calories}")

    # Macronutrients
    def _fmt_line(
        label_text: str, value: float | None, unit: str = "g", dv: float | None = None
    ) -> str | None:
        if value is None:
            return None
        dv_str = f"  {dv:.0f}%" if dv is not None else ""
        if unit == "g":
            return f"{label_text} {value:.1f}g{dv_str}"
        elif unit == "mg":
            return f"{label_text} {value:.0f}mg{dv_str}"
        return f"{label_text} {value}{unit}{dv_str}"

    # Build a list of (display_name, usda_name, value, unit) tuples
    nutrient_rows: list[tuple[str, str, float | None, str]] = [
        ("Total Fat", "Total lipid (fat)", nf.total_fat, "g"),
        ("  Saturated Fat", "Fatty acids, total saturated", nf.saturated_fat, "g"),
        ("  Trans Fat", "Fatty acids, total trans", nf.trans_fat, "g"),
        ("Cholesterol", "Cholesterol", nf.cholesterol, "mg"),
        ("Sodium", "Sodium, Na", nf.sodium, "mg"),
        ("Total Carbohydrate", "Carbohydrate, by difference", nf.total_carbohydrate, "g"),
        ("  Dietary Fiber", "Fiber, total dietary", nf.dietary_fiber, "g"),
        ("  Total Sugars", "Total Sugars", nf.total_sugars, "g"),
        ("  Includes Added Sugars", "Sugars, added", nf.added_sugars, "g"),
        ("Protein", "Protein", nf.protein, "g"),
    ]
    for display, usda_name, value, unit in nutrient_rows:
        if value is not None:
            dv = nf.daily_values.get(usda_name)
            line = _fmt_line(display, value, unit, dv)
            if line:
                lines.append(line)

    # Vitamins and minerals (only show those with DV values)
    for display, usda_name in [
        ("Vitamin D", "Vitamin D (D2 + D3)"),
        ("Calcium", "Calcium, Ca"),
        ("Iron", "Iron, Fe"),
        ("Potassium", "Potassium, K"),
    ]:
        dv = nf.daily_values.get(usda_name)
        if dv is not None:
            lines.append(f"{display}  {dv:.0f}%")

    # Footer
    lines.append("")
    lines.append(
        "* The % Daily Value tells you how much a nutrient in a serving of food "
        "contributes to a daily diet. 2,000 calories a day is used for general nutrition advice."
    )

    return "\n".join(lines)


def render_full_label(
    label: StructuredLabel,
    nf_panel: NutritionFactsPanel | None = None,
    claims: list[str] | None = None,
) -> tuple[str, str | None]:
    """Render the complete commercial label text.

    Args:
        label: Structured label data.
        nf_panel: Optional Nutrition Facts panel.
        claims: Optional list of formatted claim texts.

    Returns:
        (ingredient_text, nutrition_facts_text)
    """
    # Render ingredient list
    ingredient_text = _render_ingredient_list(label)
    if claims:
        ingredient_text = "\n".join([*claims, ingredient_text])

    # Render NF panel
    nf_text: str | None = None
    if nf_panel is not None:
        nf_text = _render_nutrition_facts(nf_panel)

    return ingredient_text, nf_text


def render_sample(sample: BenchmarkSample) -> BenchmarkSample:
    """Render a BenchmarkSample's labels using template rendering.

    Modifies the sample in-place, setting rendered_label_text
    and rendered_nutrition_facts.

    Args:
        sample: The sample to render.

    Returns:
        The same sample with rendered text fields set.
    """
    claims_texts = (
        [c.claim_text for c in sample.structured_label.claims]
        if sample.structured_label.claims
        else None
    )

    ing_text, nf_text = render_full_label(
        sample.structured_label,
        sample.nutrition_facts_json,
        claims_texts,
    )

    sample.rendered_label_text = ing_text
    sample.rendered_nutrition_facts = nf_text
    return sample


# ═══════════════════════════════════════════════════════════════════════════════
# LLM-based Refinement (optional enhancement)
# ═══════════════════════════════════════════════════════════════════════════════

# Structured prompt template for LLM surface refinement.
# The LLM is strictly limited to language-only changes.

LLM_SYSTEM_PROMPT: str = (
    "You are a food label copy editor. Your ONLY task is to rewrite the given "
    "structured ingredient list and Nutrition Facts into natural, commercially "
    "acceptable U.S. food label text.\n\n"
    """STRICT RULES — you MUST follow ALL of these:
1. Do NOT add any ingredients that are not listed.
2. Do NOT remove any ingredients that are listed.
3. Do NOT change the order of ingredients.
4. Do NOT modify any percentages, serving sizes, or nutrient amounts.
5. Do NOT change allergen declarations.
6. Do NOT change any regulatory statements or claims.
7. ONLY improve: grammar, casing, punctuation, whitespace, and natural phrasing.
8. Keep all text in UPPERCASE for ingredient lists (standard U.S. convention).
9. If an ingredient list is already well-formatted, return it unchanged.

Input format:
---
INGREDIENT LIST: <comma-separated structured ingredients>
NUTRITION FACTS: <nutrition facts text>
ALLERGENS: <allergen declaration, if any>
CLAIMS: <claims, if any>
---

Output format:
Return ONLY the formatted label text — no explanations, no commentary."""
)


def llm_refine_label(
    ingredient_text: str,
    nf_text: str | None = None,
    api_key: str | None = None,
    model: str = "gpt-4o-mini",
) -> str:
    """Optionally refine label text using an LLM.

    If no API key is provided, returns the template output unchanged.

    Args:
        ingredient_text: Template-rendered ingredient text.
        nf_text: Template-rendered Nutrition Facts text.
        api_key: LLM API key (optional).
        model: Model name to use.

    Returns:
        Refined label text, or original if LLM unavailable.
    """
    if not api_key:
        return ingredient_text

    # Build the prompt
    prompt_parts = [f"INGREDIENT LIST: {ingredient_text}"]
    if nf_text:
        prompt_parts.append(f"NUTRITION FACTS:\n{nf_text}")
    full_prompt = "\n---\n".join(prompt_parts)

    # Attempt LLM call
    try:
        refined = _call_llm(full_prompt, model, api_key, fallback=ingredient_text)
    except Exception:
        return ingredient_text
    if not _looks_like_ingredient_label(refined):
        return ingredient_text
    return refined


def _looks_like_ingredient_label(text: str) -> bool:
    """Minimal guardrail for ingredient-list-only LLM output."""
    text_upper = text.strip().upper()
    return (
        "INGREDIENTS:" in text_upper
        and "NUTRITION FACTS" not in text_upper
        and "---" not in text_upper
    )


def _call_llm(prompt: str, model: str, api_key: str, fallback: str | None = None) -> str:
    """Make an LLM API call with constraint enforcement.

    Currently supports OpenAI and Anthropic APIs.
    Falls back to original prompt on any failure.

    Args:
        prompt: The full prompt with structured data.
        model: Model name.
        api_key: API key.

    Returns:
        Refined text, or fallback on failure.
    """
    fallback_text = prompt if fallback is None else fallback

    # Attempt OpenAI
    if model.startswith("gpt") or model.startswith("o"):
        try:
            import openai  # type: ignore[import-not-found]

            client = openai.OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": LLM_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.0,  # deterministic output
                max_tokens=2000,
            )
            return response.choices[0].message.content or fallback_text
        except ImportError:
            return fallback_text  # openai not installed
        except Exception:
            return fallback_text

    # Attempt Anthropic
    if model.startswith("claude"):
        try:
            import anthropic  # type: ignore[import-not-found]

            client = anthropic.Anthropic(api_key=api_key)
            response = client.messages.create(
                model=model,
                system=LLM_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=2000,
            )
            return response.content[0].text if response.content else fallback_text
        except ImportError:
            return fallback_text
        except Exception:
            return fallback_text

    return fallback_text
