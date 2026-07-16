import os
import json
import time
from groq import Groq

client = Groq(api_key=os.environ["GROQ_API_KEY"])

MAX_CHARS = 12000  # safety limit to avoid exceeding the model's input size


def extract_recipe(messy_text):
    if not messy_text or not messy_text.strip():
        return {
            "name": None, "servings": None,
            "prep_time_minutes": None, "cook_time_minutes": None,
            "ingredients": [], "steps": [],
            "error": "No text provided"
        }

    truncated = False
    if len(messy_text) > MAX_CHARS:
        messy_text = messy_text[:MAX_CHARS]
        truncated = True

    prompt = f"""Extract this recipe into JSON with these exact keys:
name, servings, prep_time_minutes, cook_time_minutes,
ingredients (list of objects with quantity, unit, name, note),
steps (list of strings).

IMPORTANT: If the source text is written in a language other than English, you MUST translate
the recipe name, ingredient names, notes, and steps into English in your JSON output.
Do not leave any field in the original non-English script. However, keep well-known
regional ingredient or dish names in their commonly used English form (e.g. "jeera",
"paneer", "dal") rather than a literal translation, if that is how they are normally
referred to in English.

If a quantity contains clearly garbled, nonsensical, or mixed-up characters (such as random
letters mixed with numbers or symbols, which can happen when text was poorly read from a
scanned image), do NOT guess a plausible-looking number — instead, set quantity to null and
add a short note like "quantity unclear in source". However, standard fraction symbols (½, ⅓,
¼, ⅔, ¾, etc.) are always valid and should be confidently converted to their decimal or
fractional value — do not treat these as unclear.
If a quantity is written as a range (e.g. "4-5", "3-4", "1-2"), preserve the full range exactly
as written in the quantity field (e.g. "4-5") — do not collapse it to just one of the numbers.

If there are no method/steps in the source at all, return an empty list for steps.
Do NOT invent a placeholder sentence such as "no steps provided" — an empty list is correct
and expected in this situation.

Include every instruction from the source as a separate step, in the same order,
even short ones like "done" or "serve". Do not skip, merge, or summarize steps.
Exclude any conversational filler, small talk, greetings, comments to viewers,
or asides unrelated to actually preparing the dish (e.g. "let me know in the comments",
talking to people in the room, thanking viewers). Only include genuine cooking instructions.
Cross-check the ingredients list against the steps: if a step mentions using something
(e.g. an ingredient, sauce, or seasoning) that isn't already in the ingredients list, add it
to the ingredients list too, using null for quantity/unit if not stated.
If the same ingredient is mentioned more than once, merge it into a single entry instead of
listing it twice, combining quantities if possible.
If the same instruction (such as a bake time/temperature) appears more than once in the source,
in slightly different wording or as a fragment, include it only once as a clear, complete step —
do not list it multiple times.
If a time is only vaguely implied (not stated as a number), use null rather than guessing.
If something is not mentioned, use null. Do not invent anything.
If the text is not a recipe at all (no ingredients or cooking instructions),
return every field as null or an empty list — do not treat unrelated sentences as steps.
Reply with ONLY the JSON, nothing else, no markdown formatting.

If the source text contains the marker [unclear], treat that specific word or value as
unknown — do not guess what it might be. Set the corresponding field to null and add a note
like "illegible in source" if relevant.

Do not replace vague, qualitative descriptions in the source (such as "a small amount",
"a pinch", "a small border", "some") with an invented specific number or measurement.
Keep the original vague wording as the note or value if no exact figure is given.

If the source text contains more than one distinct, complete recipe, only extract the first
recipe and ignore the rest. Always return a single JSON object, never a list or array of
multiple recipes.


Recipe text:
{messy_text}"""

    try:
        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[{"role": "user", "content": prompt}],
        )
        raw_text = response.choices[0].message.content.strip()

        if raw_text.startswith("```"):
            raw_text = raw_text.strip("`")
            raw_text = raw_text.replace("json", "", 1).strip()

        recipe_dict = json.loads(raw_text)

        if isinstance(recipe_dict, list):
            return {
                "name": None, "servings": None,
                "prep_time_minutes": None, "cook_time_minutes": None,
                "ingredients": [], "steps": [],
                "error": "This source appears to contain multiple recipes. Please provide "
                         "an image or text with only one recipe."
            }

        if truncated:
            existing_note = recipe_dict.get("note", "") or ""
            recipe_dict["note"] = (
                existing_note + " Source text was very long and had to be shortened; "
                "some details near the end may be missing."
            ).strip()

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
        "",
        """
        आलू पराठा - 4 लोगों के लिए
        2 कप आटा, 3 उबले आलू, नमक, लाल मिर्च, थोड़ा घी चाहिए
        सब कुछ मिलाएं, आटा गूंथें, आलू भरें, बेलें और तवे पर सुनहरा होने तक तलें
        """,
        "chop onions. " * 5000,
    ]

    for i, text in enumerate(test_cases, start=1):
        print(f"\n--- TEST CASE {i} ---")
        result = extract_recipe(text)
        print(result)
        time.sleep(2)