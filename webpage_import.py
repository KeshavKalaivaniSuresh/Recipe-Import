from recipe_scrapers import scrape_me
from extractor import extract_recipe


def safe_get(func, default=None):
    try:
        return func()
    except Exception:
        return default


def empty_recipe_with_error(message):
    return {
        "name": None, "servings": None,
        "prep_time_minutes": None, "cook_time_minutes": None,
        "ingredients": [], "steps": [], "image": None,
        "error": message
    }


PAYWALL_KEYWORDS = [
    "subscribe to view", "subscribe to read", "sign in to view",
    "sign in to read", "members only", "subscribe to continue",
    "become a member", "premium content", "log in to view"
]


def fetch_recipe_from_url(url):
    try:
        scraper = scrape_me(url)
    except Exception as e:
        error_text = str(e)
        if "403" in error_text or "Forbidden" in error_text:
            return empty_recipe_with_error(
                "This website blocked automated access. Try pasting the recipe text instead."
            )
        elif "404" in error_text or "Not Found" in error_text:
            return empty_recipe_with_error(
                "This page could not be found. Please check the link is correct."
            )
        elif "timeout" in error_text.lower():
            return empty_recipe_with_error(
                "The website took too long to respond. Please try again later."
            )
        else:
            return empty_recipe_with_error(f"Could not read this page: {error_text}")

    raw_ingredients = safe_get(scraper.ingredients, default=[])
    raw_steps = safe_get(scraper.instructions_list, default=[])

    if not raw_ingredients and not raw_steps:
        return empty_recipe_with_error(
            "No recipe content could be found on this page."
        )

    if raw_ingredients and not raw_steps:
        return empty_recipe_with_error(
            "This looks like a recipe listing or collection page, not a single recipe. "
            "Please use the link to one specific recipe."
        )

    combined_check_text = " ".join(raw_ingredients + raw_steps).lower()
    if any(keyword in combined_check_text for keyword in PAYWALL_KEYWORDS):
        return empty_recipe_with_error(
            "This recipe appears to be behind a paywall or login and can't be fully read. "
            "Please use a publicly accessible recipe, or paste the text instead."
        )

    combined_text = "Ingredients:\n" + "\n".join(raw_ingredients) + "\n\nSteps:\n" + "\n".join(raw_steps)
    structured = extract_recipe(combined_text)

    structured["name"] = safe_get(scraper.title) or structured.get("name")
    structured["servings"] = safe_get(scraper.yields) or structured.get("servings")
    structured["cook_time_minutes"] = safe_get(scraper.total_time) or structured.get("cook_time_minutes")
    structured["image"] = safe_get(scraper.image)

    return structured


if __name__ == "__main__":
    test_urls = [
        "https://www.bbcgoodfood.com/recipes/easy-pancakes",
        "https://www.allrecipes.com/recipe/158968/spinach-and-feta-turkey-burgers/",
        "https://pinchofyum.com/the-best-soft-chocolate-chip-cookies",
        "https://www.bbcgoodfood.com/recipes/collection/pancake-recipes",
        "https://www.bbcgoodfood.com/recipes/this-page-does-not-exist-xyz123",
    ]

    for url in test_urls:
        print(f"\n--- {url} ---")
        result = fetch_recipe_from_url(url)
        if result.get("error"):
            print(f"ERROR: {result['error']}")
        else:
            print(f"name: {result['name']}")
            print(f"servings: {result['servings']}")
            print(f"ingredients: {result['ingredients']}")
            print(f"steps: {result['steps']}")