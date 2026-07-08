import os
import json
import time
import google.generativeai as genai

genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-2.5-flash")


def extract_recipe(messy_text):
    # Guard: don't even call the API for empty input
    if not messy_text or not messy_text.strip():
        return {
            "name": None, "servings": None,
            "prep_time_minutes": None, "cook_time_minutes": None,
            "ingredients": [], "steps": [],
            "error": "No text provided"
        }

    prompt = f"""Extract this recipe into JSON with these exact keys:
name, servings, prep_time_minutes, cook_time_minutes,
ingredients (list of objects with quantity, unit, name, note),
steps (list of strings).
Include every instruction from the source as a separate step, in the same order,
even short ones like "done" or "serve". Do not skip, merge, or summarize steps.
If a time is only vaguely implied (not stated as a number), use null rather than guessing.
If something is not mentioned, use null. Do not invent anything.
Reply with ONLY the JSON, nothing else, no markdown formatting.

Recipe text:
{messy_text}"""

    try:
        response = model.generate_content(prompt)
        raw_text = response.text.strip()

        if raw_text.startswith("```"):
            raw_text = raw_text.strip("`")
            raw_text = raw_text.replace("json", "", 1).strip()

        recipe_dict = json.loads(raw_text)
        return recipe_dict

    except Exception as e:
        # Never crash — return a clear, safe result instead
        return {
            "name": None, "servings": None,
            "prep_time_minutes": None, "cook_time_minutes": None,
            "ingredients": [], "steps": [],
            "error": f"Extraction failed: {e}"
        }

if __name__ == "__main__":
    test_cases = [
        # Case 1: normal, like before
        """
        aloo paratha
        serves 4
        need 2 cups atta, 3 boiled potatoes (mashed), salt, chili powder, some ghee
        mix everything, make dough, stuff with potato, roll and fry on tawa till golden
        """,

        # Case 2: messy, no servings, fractions, regional ingredient name
        """
        quick jeera rice - just microwave rice, 1-2 tsp jeera, ½ cup peas, ghee.
        heat ghee, add jeera till it splutters, add rice and peas, mix, done
        """,

        # Case 3: barely any structure at all
        """
        my grandma's chutney: coconut, green chili, curry leaves, tamarind, salt.
        grind it all up with a little water.
        """,
        
        # Case 4: has explicit prep/cook time
        """
        omelette - prep 5 mins, cook 3 mins.
        2 eggs, pinch of salt, splash of milk. whisk and fry.
        """,

        # Case 5: not a recipe at all
        """
        just wanted to say the weather is really nice today, hope you're doing well.
        """,

        # Case 6: empty input
        ""
    ]

    for i, text in enumerate(test_cases, start=1):
        print(f"\n--- TEST CASE {i} ---")
        result = extract_recipe(text)
        print(result)
        time.sleep(15)