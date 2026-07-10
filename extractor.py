import os
import json
import time
from groq import Groq

client = Groq(api_key=os.environ["GROQ_API_KEY"])


def extract_recipe(messy_text):
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
Exclude any conversational filler, small talk, greetings, comments to viewers,
or asides unrelated to actually preparing the dish (e.g. "let me know in the comments",
talking to people in the room, thanking viewers). Only include genuine cooking instructions.
If a time is only vaguely implied (not stated as a number), use null rather than guessing.
If something is not mentioned, use null. Do not invent anything.
If the text is not a recipe at all (no ingredients or cooking instructions),
return every field as null or an empty list — do not treat unrelated sentences as steps.
Reply with ONLY the JSON, nothing else, no markdown formatting.

Recipe text:
{messy_text}"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
        )
        raw_text = response.choices[0].message.content.strip()

        if raw_text.startswith("```"):
            raw_text = raw_text.strip("`")
            raw_text = raw_text.replace("json", "", 1).strip()

        recipe_dict = json.loads(raw_text)
        return recipe_dict

    except Exception as e:
        return {
            "name": None, "servings": None,
            "prep_time_minutes": None, "cook_time_minutes": None,
            "ingredients": [], "steps": [],
            "error": f"Extraction failed: {e}"
        }


if __name__ == "__main__":
    test_cases = [
        """
        aloo paratha
        serves 4
        need 2 cups atta, 3 boiled potatoes (mashed), salt, chili powder, some ghee
        mix everything, make dough, stuff with potato, roll and fry on tawa till golden
        """,
        """
        quick jeera rice - just microwave rice, 1-2 tsp jeera, ½ cup peas, ghee.
        heat ghee, add jeera till it splutters, add rice and peas, mix, done
        """,
        """
        my grandma's chutney: coconut, green chili, curry leaves, tamarind, salt.
        grind it all up with a little water.
        """,
        """
        omelette - prep 5 mins, cook 3 mins.
        2 eggs, pinch of salt, splash of milk. whisk and fry.
        """,
        """
        just wanted to say the weather is really nice today, hope you're doing well.
        """,
        ""
    ]

    for i, text in enumerate(test_cases, start=1):
        print(f"\n--- TEST CASE {i} ---")
        result = extract_recipe(text)
        print(result)
        time.sleep(2)  