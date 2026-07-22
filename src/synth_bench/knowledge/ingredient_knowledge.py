"""Ingredient knowledge base.

Provides:
  - USDA standard name → commercial label name synonym dictionary
  - Compound ingredient expansion tables
  - Ingredient category/taxonomy mappings
  - Common food additive mapping
"""

from __future__ import annotations

import re

# ── USDA Standard Name → Commercial Label Name ───────────────────────────────
#
# FNDDS uses USDA standard descriptions (e.g. "Milk, whole, 3.25% milkfat ...
# with added vitamin D"). Commercial labels use short names (e.g. "MILK").
# This dictionary provides the mapping.

STANDARD_TO_COMMERCIAL: dict[str, str] = {
    # ── Dairy ──
    "Milk, whole, 3.25% milkfat, with added vitamin D": "MILK",
    "Milk, reduced fat, fluid, 2% milkfat, with added vitamin A and vitamin D": "REDUCED FAT MILK",
    "Milk, lowfat, fluid, 1% milkfat, with added vitamin A and vitamin D": "LOWFAT MILK",
    "Milk, nonfat, fluid, with added vitamin A and vitamin D (fat free or skim)": "NONFAT MILK",
    "Milk, NFS": "MILK",
    "Milk, buttermilk, fluid, cultured, lowfat": "BUTTERMILK",
    "Cheese, cheddar": "CHEDDAR CHEESE",
    "Cheese, mozzarella, low moisture, part skim": "MOZZARELLA CHEESE",
    "Cheese, parmesan, grated": "PARMESAN CHEESE",
    "Cheese, cream": "CREAM CHEESE",
    "Cheese, cottage, lowfat, 1% milkfat": "COTTAGE CHEESE",
    "Cheese, ricotta, part skim": "RICOTTA CHEESE",
    "Cheese, swiss": "SWISS CHEESE",
    "Cheese, provolone": "PROVOLONE CHEESE",
    "Yogurt, plain, low fat": "LOWFAT YOGURT",
    "Yogurt, plain, whole milk": "YOGURT",
    "Yogurt, fruit, low fat": "FRUIT YOGURT",
    "Ice cream, vanilla": "ICE CREAM",
    "Ice cream, chocolate": "CHOCOLATE ICE CREAM",
    "Butter, salted": "BUTTER",
    "Butter, without salt": "BUTTER",
    "Whipped cream, pressurized": "WHIPPED CREAM",
    # ── Grains ──
    "Wheat flour, all-purpose, enriched, bleached": "ENRICHED WHEAT FLOUR",
    "Wheat flour, whole-grain": "WHOLE WHEAT FLOUR",
    "Bread, white, prepared from recipe, made with low fat (2%) milk": "WHITE BREAD",
    "Bread, whole wheat, commercially prepared": "WHOLE WHEAT BREAD",
    "Bread, reduced-calorie, oat bran": "OAT BRAN BREAD",
    "Roll, white, hamburger or hotdog": "BUN",
    "Bagel, plain, enriched, with calcium propionate (includes onion, poppy, sesame)": "BAGEL",
    "Crackers, saltines, low fat (includes oyster, soda, soup)": "SALTINE CRACKERS",
    "Crackers, graham": "GRAHAM CRACKERS",
    "Cereal, ready-to-eat, corn flakes, plain": "CORN FLAKES",
    "Cereal, ready-to-eat, granola, homemade": "GRANOLA",
    "Cereal, oats, regular and quick, not fortified, dry": "OATS",
    "Rice, white, long-grain, regular, enriched, cooked": "WHITE RICE",
    "Rice, brown, long-grain, cooked": "BROWN RICE",
    "Pasta, cooked, enriched, without added salt": "PASTA",
    "Noodles, egg, cooked, enriched, without added salt": "EGG NOODLES",
    # ── Sweeteners ──
    "Sugar, granulated": "SUGAR",
    "Sugar, brown": "BROWN SUGAR",
    "Sugar, powdered": "POWDERED SUGAR",
    "Syrup, maple": "MAPLE SYRUP",
    "Syrup, corn, high-fructose": "HIGH FRUCTOSE CORN SYRUP",
    "Syrup, corn, light": "CORN SYRUP",
    "Honey": "HONEY",
    "Molasses": "MOLASSES",
    "Jams and preserves, apricot": "APRICOT JAM",
    "Jams and preserves, strawberry": "STRAWBERRY JAM",
    "Jelly, any flavor": "JELLY",
    # ── Oils & Fats ──
    "Oil, vegetable, corn, canola and palm": "VEGETABLE OIL",
    "Oil, olive, salad or cooking": "OLIVE OIL",
    "Oil, soybean, salad or cooking": "SOYBEAN OIL",
    "Oil, canola": "CANOLA OIL",
    "Oil, corn, salad or cooking": "CORN OIL",
    "Shortening, vegetable, household, composite": "VEGETABLE SHORTENING",
    "Margarine, regular, 80% fat, stick": "MARGARINE",
    "Margarine, soft, 60% fat": "MARGARINE SPREAD",
    "Salad dressing, mayonnaise, regular": "MAYONNAISE",
    "Salad dressing, ranch, regular": "RANCH DRESSING",
    "Salad dressing, italian, regular": "ITALIAN DRESSING",
    # ── Meats ──
    "Chicken, broiler or fryers, breast, skinless, boneless, meat only, cooked, roasted": "CHICKEN BREAST",  # noqa: E501
    "Chicken, broiler, rotisserie, BBQ, breast, meat and skin": "BBQ CHICKEN",
    "Beef, ground, 80% lean / 20% fat, patty, cooked, pan-broiled": "GROUND BEEF",
    "Beef, ground, 90% lean / 10% fat, patty, cooked, pan-broiled": "LEAN GROUND BEEF",
    "Beef, loin, sirloin steak, separable lean and fat, trimmed to 0 inch fat, all grades, cooked, grilled": "SIRLOIN STEAK",  # noqa: E501
    "Pork, cured, ham, regular (approximately 13% fat), canned, roasted": "HAM",
    "Pork, fresh, loin, center rib (rib chops), bone-in, separable lean and fat, cooked, pan-fried": "PORK CHOP",  # noqa: E501
    "Turkey, whole, meat and skin, cooked, roasted": "TURKEY",
    "Bacon, pork, microwaved": "BACON",
    "Sausage, Italian, pork, cooked": "ITALIAN SAUSAGE",
    "Sausage, beef, smoked": "SMOKED SAUSAGE",
    # ── Seafood ──
    "Fish, salmon, Atlantic, farmed, cooked, dry heat": "SALMON",
    "Fish, tuna, light, canned in water, drained solids": "TUNA",
    "Fish, cod, Atlantic, cooked, dry heat": "COD",
    "Shrimp, mixed species, cooked, moist heat (may contain additives to retain moisture)": "SHRIMP",  # noqa: E501
    "Crustaceans, crab, alaska king, cooked, moist heat": "CRAB",
    # ── Eggs ──
    "Egg, whole, raw": "EGGS",
    "Egg, white, raw, frozen, pasteurized": "EGG WHITES",
    "Egg, yolk, raw, fresh": "EGG YOLK",
    # ── Fruits ──
    "Apple, raw, with skin": "APPLES",
    "Apple, raw, without skin": "APPLES",
    "Banana, raw": "BANANAS",
    "Orange, raw, navel": "ORANGES",
    "Orange, raw, California": "ORANGES",
    "Grapes, red or green (European type, such as Thompson seedless), raw": "GRAPES",
    "Strawberries, raw": "STRAWBERRIES",
    "Blueberries, raw": "BLUEBERRIES",
    "Raisins, seedless": "RAISINS",
    "Avocado, raw, Florida": "AVOCADO",
    "Lemon juice, raw": "LEMON JUICE",
    "Fruit juice blend, 100% juice": "100% FRUIT JUICE",
    "Orange juice, raw": "ORANGE JUICE",
    "Apple juice, ready-to-drink": "APPLE JUICE",
    # ── Vegetables ──
    "Onions, raw": "ONIONS",
    "Onions, yellow, raw": "ONIONS",
    "Onions, red, raw": "RED ONIONS",
    "Tomatoes, red, ripe, raw": "TOMATOES",
    "Tomato products, canned, sauce": "TOMATO SAUCE",
    "Tomato products, canned, paste": "TOMATO PASTE",
    "Tomato products, canned, puree": "TOMATO PUREE",
    "Potatoes, Russet, flesh and skin, raw": "POTATOES",
    "Potatoes, red, flesh and skin, raw": "RED POTATOES",
    "Carrots, raw": "CARROTS",
    "Celery, raw": "CELERY",
    "Lettuce, cos or romaine, raw": "ROMANE LETTUCE",
    "Spinach, raw": "SPINACH",
    "Broccoli, raw": "BROCCOLI",
    "Cauliflower, raw": "CAULIFLOWER",
    "Bell peppers, sweet, red, raw": "RED BELL PEPPERS",
    "Bell peppers, sweet, green, raw": "GREEN BELL PEPPERS",
    "Garlic, raw": "GARLIC",
    "Ginger, raw": "GINGER",
    "Mushrooms, white, raw": "MUSHROOMS",
    "Corn, sweet, yellow, raw": "CORN",
    "Peas, green, frozen, unprepared": "GREEN PEAS",
    "Beans, snap, green, raw": "GREEN BEANS",
    # ── Legumes ──
    "Beans, kidney, all types, mature seeds, cooked, boiled, without salt": "KIDNEY BEANS",
    "Beans, black, mature seeds, cooked, boiled, without salt": "BLACK BEANS",
    "Chickpeas (garbanzo beans, bengal gram), mature seeds, cooked, boiled, without salt": "CHICKPEAS",  # noqa: E501
    "Lentils, mature seeds, cooked, boiled, without salt": "LENTILS",
    "Peanut butter, smooth style, without salt": "PEANUT BUTTER",
    "Soymilk, original and vanilla, unfortified": "SOYMILK",
    "Tofu, raw, regular, prepared with calcium sulfate": "TOFU",
    "Tofu, soft, prepared with calcium sulfate and magnesium chloride (nigari)": "SOFT TOFU",
    # ── Nuts ──
    "Nuts, almonds, raw": "ALMONDS",
    "Nuts, walnuts, english": "WALNUTS",
    "Nuts, cashew nuts, raw": "CASHEWS",
    "Nuts, pecans, raw": "PECANS",
    "Seeds, sunflower seed kernels, dried": "SUNFLOWER SEEDS",
    "Coconut, raw, meat": "COCONUT",
    # ── Spices & Herbs ──
    "Salt, table": "SALT",
    "Spices, pepper, black": "BLACK PEPPER",
    "Spices, cinnamon, ground": "CINNAMON",
    "Spices, paprika": "PAPRIKA",
    "Spices, cumin seed": "CUMIN",
    "Spices, chili powder": "CHILI POWDER",
    "Spices, oregano, dried": "OREGANO",
    "Spices, garlic powder": "GARLIC POWDER",
    "Spices, onion powder": "ONION POWDER",
    "Vanilla extract": "VANILLA EXTRACT",
    "Baking powder, double-acting, straight phosphate": "BAKING POWDER",
    "Baking soda": "BAKING SODA",
    "Yeast, baker's, active dry": "YEAST",
    "Vinegar, distilled": "VINEGAR",
    # ── Additives ──
    "Water, tap": "WATER",
    "Water, bottled, generic": "WATER",
    "Vital wheat gluten": "WHEAT GLUTEN",
    "Xanthan gum": "XANTHAN GUM",
    "Soy lecithin": "SOY LECITHIN",
    # ── Compound/Specialty ──
    "Chocolate, dark, 70-85% cacao solids": "DARK CHOCOLATE",
    "Chocolate, milk": "MILK CHOCOLATE",
    "Chocolate, white": "WHITE CHOCOLATE",
    "Cocoa, dry powder, unsweetened": "COCOA POWDER",
    "Whey, acid, fluid": "WHEY",
    "Whey, sweet, fluid": "WHEY",
    "Milk, dry, nonfat, instant, with added vitamin A and vitamin D": "NONFAT DRY MILK",
    "Milk, dry, whole": "WHOLE DRY MILK",
    "Cheese, parmesan, shredded": "SHREDDED PARMESAN CHEESE",
    "Bread crumbs, dry, grated, plain": "BREAD CRUMBS",
}


# ── Generic Name Mapping ──────────────────────────────────────────────────────
# Maps specific cultivar/variety names to generic descriptions

GENERIC_NAME_MAP: dict[str, str] = {
    # Fruits
    "Granny Smith": "APPLES",
    "Red Delicious": "APPLES",
    "Fuji": "APPLES",
    "Gala": "APPLES",
    "Honeycrisp": "APPLES",
    "Navel": "ORANGES",
    "Valencia": "ORANGES",
    "Cara Cara": "ORANGES",
    "Blood": "ORANGES",
    "Thompson seedless": "GRAPES",
    "Concord": "GRAPES",
    "Red seedless": "GRAPES",
    "Green seedless": "GRAPES",
    # Vegetables
    "Russet": "POTATOES",
    "Yukon Gold": "POTATOES",
    "Red": "POTATOES",
    "Fingerling": "POTATOES",
    "Sweet": "SWEET POTATOES",
    "Roma": "TOMATOES",
    "Beefsteak": "TOMATOES",
    "Cherry": "TOMATOES",
    "Grape": "TOMATOES",
    "Heirloom": "TOMATOES",
    "Cos": "LETTUCE",
    "Iceberg": "LETTUCE",
    "Butter": "LETTUCE",
    # Cheese
    "Cheddar": "CHEESE",
    "Mozzarella": "CHEESE",
    "Swiss": "CHEESE",
    "Provolone": "CHEESE",
    "Monterey Jack": "CHEESE",
    "Pepper Jack": "CHEESE",
    "Colby": "CHEESE",
    "Gouda": "CHEESE",
    "Havarti": "CHEESE",
    "Brie": "CHEESE",
    "Camembert": "CHEESE",
    "Gruyere": "CHEESE",
    "Feta": "CHEESE",
    "Blue": "CHEESE",
    "Gorgonzola": "CHEESE",
    "Parmesan": "CHEESE",
    "Ricotta": "CHEESE",
    "Cottage": "COTTAGE CHEESE",
}


# ── Compound Ingredient Expansion ─────────────────────────────────────────────
# When a compound ingredient appears, these rules define its sub-ingredients.
# The fractions are approximate composition within the compound.

CompoundRecipe = list[tuple[str, float]]

COMPOUND_INGREDIENTS: dict[str, CompoundRecipe] = {
    "Chocolate": [
        ("cocoa mass", 0.40),
        ("sugar", 0.40),
        ("cocoa butter", 0.15),
        ("soy lecithin", 0.03),
        ("vanilla extract", 0.02),
    ],
    "Milk Chocolate": [
        ("sugar", 0.47),
        ("milk", 0.20),
        ("cocoa mass", 0.15),
        ("cocoa butter", 0.15),
        ("soy lecithin", 0.02),
        ("vanilla extract", 0.01),
    ],
    "White Chocolate": [
        ("sugar", 0.45),
        ("cocoa butter", 0.25),
        ("milk", 0.22),
        ("soy lecithin", 0.03),
        ("vanilla extract", 0.01),
        ("salt", 0.02),
    ],
    "Ketchup": [
        ("tomato concentrate", 0.60),
        ("sugar", 0.15),
        ("vinegar", 0.10),
        ("salt", 0.04),
        ("spices", 0.01),
        ("water", 0.10),
    ],
    "Mayonnaise": [
        ("soybean oil", 0.65),
        ("egg yolk", 0.10),
        ("vinegar", 0.08),
        ("water", 0.15),
        ("sugar", 0.01),
        ("salt", 0.01),
        ("lemon juice", 0.01),
    ],
    "Mustard": [
        ("vinegar", 0.40),
        ("water", 0.30),
        ("mustard seed", 0.18),
        ("salt", 0.05),
        ("turmeric", 0.03),
        ("spices", 0.02),
    ],
    "BBQ Sauce": [
        ("tomato puree", 0.40),
        ("sugar", 0.25),
        ("vinegar", 0.15),
        ("molasses", 0.10),
        ("spices", 0.05),
        ("salt", 0.02),
        ("smoke flavor", 0.01),
    ],
    "Soy Sauce": [
        ("water", 0.60),
        ("soybeans", 0.15),
        ("wheat", 0.10),
        ("salt", 0.10),
        ("sugar", 0.03),
    ],
    "Vinaigrette": [
        ("vegetable oil", 0.50),
        ("vinegar", 0.30),
        ("water", 0.15),
        ("salt", 0.02),
        ("spices", 0.02),
        ("sugar", 0.01),
    ],
    "Pizza Sauce": [
        ("tomato puree", 0.80),
        ("vegetable oil", 0.05),
        ("salt", 0.03),
        ("sugar", 0.03),
        ("garlic", 0.02),
        ("oregano", 0.02),
        ("basil", 0.01),
    ],
    "Enriched Flour": [
        ("wheat flour", 0.985),
        ("niacin", 0.002),
        ("iron", 0.006),
        ("thiamine mononitrate", 0.001),
        ("riboflavin", 0.001),
        ("folic acid", 0.001),
    ],
    "Bread Crumbs": [
        ("wheat flour", 0.80),
        ("yeast", 0.05),
        ("sugar", 0.05),
        ("salt", 0.03),
        ("vegetable oil", 0.02),
    ],
    "Shortcrust Pastry": [
        ("wheat flour", 0.45),
        ("butter", 0.30),
        ("water", 0.15),
        ("sugar", 0.05),
        ("egg", 0.05),
    ],
    "Puff Pastry": [
        ("wheat flour", 0.35),
        ("butter", 0.45),
        ("water", 0.18),
        ("salt", 0.02),
    ],
    "Seasoning Blend": [
        ("salt", 0.30),
        ("spices", 0.25),
        ("sugar", 0.15),
        ("dehydrated vegetables", 0.12),
        ("natural flavor", 0.08),
        ("garlic powder", 0.05),
        ("onion powder", 0.05),
    ],
    "Chicken Stock": [
        ("water", 0.80),
        ("chicken", 0.10),
        ("vegetables", 0.05),
        ("salt", 0.02),
        ("flavor", 0.01),
    ],
    "Vegetable Stock": [
        ("water", 0.85),
        ("vegetables", 0.10),
        ("salt", 0.02),
        ("spices", 0.01),
        ("sugar", 0.01),
    ],
}


# ── Ingredient Category Classification ────────────────────────────────────────
# Maps ingredient keywords to broad categories, used for FoodOn-like taxonomy


INGREDIENT_CATEGORIES: dict[str, str] = {
    "dairy": r"\b(milk|cream|cheese|yogurt|whey|butter|custard|buttermilk)\b",
    "egg": r"\b(egg|egg white|egg yolk|albumin)\b",
    "grain": r"\b(flour|wheat|rye|barley|oats|corn|rice|pasta|noodle|cracker|bread)\b",
    "sweetener": r"\b(sugar|syrup|honey|molasses|sucrose|fructose|glucose|dextrose|maltose|aspartame|stevia|splenda)\b",  # noqa: E501
    "oil_fat": r"\b(oil|shortening|lard|margarine|fat|tallow)\b",
    "fruit": r"\b(fruit|apple|banana|orange|grape|berry|lemon|strawberry)\b",
    "vegetable": r"\b(onion|garlic|tomato|carrot|celery|lettuce|broccoli|spinach|potato|corn|pea|bean)\b",  # noqa: E501
    "meat": r"\b(chicken|beef|pork|turkey|ham|bacon|lamb|veal|sausage|meat)\b",
    "seafood": r"\b(salmon|tuna|cod|shrimp|crab|lobster|fish|clam|mussel)\b",
    "nut": r"\b(almond|walnut|cashew|peanut|pecan|hazelnut|nut)\b",
    "herb_spice": r"\b(salt|pepper|cinnamon|oregano|basil|cumin|paprika|garlic powder|onion powder)\b",  # noqa: E501
    "additive": r"\b(lecithin|gum|xanthan|guar|carrageenan|cellulose|phosphate|citrate)\b",
    "water": r"\b(water|broth|stock|juice)\b",
    "legume": r"\b(soy|lentil|chickpea|tofu|edamame|miso)\b",
    "alcohol": r"\b(wine|beer|vodka|whiskey|rum|sherry|liqueur|alcohol|brandy)\b",
}

_CATEGORY_PATTERNS: dict[str, re.Pattern] = {
    name: re.compile(pattern, re.I) for name, pattern in INGREDIENT_CATEGORIES.items()
}


# ── Allergen Keyword Mapping ──────────────────────────────────────────────────

FDA_MAJOR_ALLERGENS: list[str] = [
    "milk",
    "eggs",
    "fish",
    "crustacean shellfish",
    "tree nuts",
    "peanuts",
    "wheat",
    "soybeans",
    "sesame",
]

# Map ingredient keywords to FDA allergens
ALLERGEN_KEYWORDS: dict[str, str] = {
    # Milk/Dairy
    "milk": "milk",
    "cream": "milk",
    "cheese": "milk",
    "yogurt": "milk",
    "whey": "milk",
    "butter": "milk",
    "buttermilk": "milk",
    "custard": "milk",
    "lactose": "milk",
    "casein": "milk",
    # Eggs
    "egg": "eggs",
    "egg white": "eggs",
    "egg yolk": "eggs",
    "albumin": "eggs",
    "albumen": "eggs",
    # Fish
    "salmon": "fish",
    "tuna": "fish",
    "cod": "fish",
    "fish": "fish",
    "anchovy": "fish",
    "sardine": "fish",
    # Shellfish
    "shrimp": "crustacean shellfish",
    "crab": "crustacean shellfish",
    "lobster": "crustacean shellfish",
    "crawfish": "crustacean shellfish",
    "prawn": "crustacean shellfish",
    # Tree nuts
    "almond": "tree nuts",
    "walnut": "tree nuts",
    "cashew": "tree nuts",
    "pecan": "tree nuts",
    "hazelnut": "tree nuts",
    "macadamia": "tree nuts",
    "pistachio": "tree nuts",
    "pine nut": "tree nuts",
    # Peanuts
    "peanut": "peanuts",
    "groundnut": "peanuts",
    # Wheat/Gluten
    "wheat": "wheat",
    "gluten": "wheat",
    "semolina": "wheat",
    "spelt": "wheat",
    # Soy
    "soy": "soybeans",
    "soybean": "soybeans",
    "tofu": "soybeans",
    "edamame": "soybeans",
    "miso": "soybeans",
    "tempeh": "soybeans",
    # Sesame
    "sesame": "sesame",
    "tahini": "sesame",
    "benne": "sesame",
}

_ALLERGEN_PATTERNS: dict[str, re.Pattern[str]] = {
    keyword: re.compile(rf"(?<![a-z0-9]){re.escape(keyword)}s?(?![a-z0-9])", re.I)
    for keyword in ALLERGEN_KEYWORDS
}

_ALLERGEN_FALSE_POSITIVE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bcream\s+of\s+tartar\b", re.I),
]

# ── Public API ────────────────────────────────────────────────────────────────


def lookup_commercial_name(fndds_name: str) -> str:
    """Look up the commercial label name for a standardized FNDDS ingredient.

    Args:
        fndds_name: The USDA FNDDS ingredient description.

    Returns:
        Commercial label name, or the original if not found.
    """
    return STANDARD_TO_COMMERCIAL.get(fndds_name, fndds_name.upper())


def make_generic(specific_name: str) -> str:
    """Replace a specific variety/cultivar name with its generic form.

    Args:
        specific_name: Ingredient name that may contain a specific variety.

    Returns:
        Generic version, or the original if no match.
    """
    return GENERIC_NAME_MAP.get(specific_name, specific_name)


def expand_compound(compound_name: str) -> CompoundRecipe | None:
    """Get the sub-ingredient recipe for a compound ingredient.

    Args:
        compound_name: Name of the compound ingredient (e.g. 'Chocolate').

    Returns:
        List of (ingredient_name, fraction) tuples, or None if unknown.
    """
    return COMPOUND_INGREDIENTS.get(compound_name)


def classify_ingredient(name: str) -> str | None:
    """Classify an ingredient into a broad category.

    Args:
        name: Ingredient name.

    Returns:
        Category string (e.g. 'dairy', 'grain'), or None if unclassified.
    """
    for category, pattern in _CATEGORY_PATTERNS.items():
        if pattern.search(name):
            return category
    return None


def detect_allergens(ingredient_names: list[str]) -> list[str]:
    """Detect FDA major allergens from a list of ingredient names.

    Args:
        ingredient_names: List of ingredient description strings.

    Returns:
        Sorted list of unique allergen names present.
    """
    allergens: set[str] = set()
    for name in ingredient_names:
        if any(pattern.search(name) for pattern in _ALLERGEN_FALSE_POSITIVE_PATTERNS):
            continue
        for keyword, allergen in ALLERGEN_KEYWORDS.items():
            if _ALLERGEN_PATTERNS[keyword].search(name):
                allergens.add(allergen)
    return sorted(allergens)
