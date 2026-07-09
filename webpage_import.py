from recipe_scrapers import scrape_me
from extractor import extract_recipe


def safe_get(func, default=None):
    try:
        return func()
    except Exception:
        return default


def fetch_recipe_from_url(url):
    try:
        scraper = scrape_me(url)
    except Exception as e:
        print(f"Could not read this page as a recipe: {e}")
        return None

    raw_ingredients = safe_get(scraper.ingredients, default=[])
    raw_steps = safe_get(scraper.instructions_list, default=[])

    # Join the raw scraped text into one block, then let extract_recipe
    # split it properly into quantity/unit/name/note and clean steps
    combined_text = "Ingredients:\n" + "\n".join(raw_ingredients) + "\n\nSteps:\n" + "\n".join(raw_steps)
    structured = extract_recipe(combined_text)

    # Fill in the fields the scraper already gave us directly (no AI needed for these)
    structured["name"] = safe_get(scraper.title) or structured.get("name")
    structured["servings"] = safe_get(scraper.yields) or structured.get("servings")
    structured["cook_time_minutes"] = safe_get(scraper.total_time) or structured.get("cook_time_minutes")
    structured["image"] = safe_get(scraper.image)

    return structured


if __name__ == "__main__":
    test_url = "https://www.bbcgoodfood.com/recipes/easy-pancakes"
    recipe_data = fetch_recipe_from_url(test_url)

    if recipe_data:
        print("FINAL STRUCTURED RECIPE:")
        for key, value in recipe_data.items():
            print(f"{key}: {value}")
    else:
        print("No recipe data found on this page.")