Smart Recipe Import — Full Progress Handoff
Project Context
ShopConnect internship project: build a feature that extracts recipe data from a webpage, YouTube video, image/PDF, or pasted text, and structures it into clean fields. Full requirements in the original problem statement PDF (already reviewed in detail). Provided HTML interface not yet received from supervisor — all work so far is backend/extraction logic only, testable standalone.
Architecture
Four source-specific files all funnel into one shared core (extractor.py), which turns any messy text into structured JSON via an LLM. This avoids duplicating cleanup logic across sources.
Pasted text ─────────────────┐
Webpage (scraped)  ──────────┼──► extract_recipe() ──► structured JSON ──► (form, pending)
YouTube (title+desc+transcript)┤
Image/PDF (vision AI / OCR) ─┘
Environment Setup (already done)

Python 3.14, VS Code (with Python extension, trust mode enabled)
Git + GitHub repo: https://github.com/KeshavKalaivaniSuresh/Recipe-Import
Groq API key set as environment variable GROQ_API_KEY (switched from Gemini due to restrictive free-tier quotas)
Tesseract OCR installed (via winget), added to PATH — used only for PDFs now
Poppler installed (manual zip extract to Desktop), added to PATH — required by pdf2image
opencv-python installed — used for blur detection

Current Complete Files
extractor.py
pythonimport os
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
If there are no method/steps in the source at all, return an empty list for steps.
Do NOT invent a placeholder sentence such as "no steps provided" — an empty list is correct
and expected in this situation.
If a quantity contains clearly garbled, nonsensical, or mixed-up characters (such as random
letters mixed with numbers or symbols, which can happen when text was poorly read from a
scanned image), do NOT guess a plausible-looking number — instead, set quantity to null and
add a short note like "quantity unclear in source". However, standard fraction symbols (½, ⅓,
¼, ⅔, ¾, etc.) are always valid and should be confidently converted to their decimal or
fractional value — do not treat these as unclear.
If a quantity is written as a range (e.g. "4-5", "3-4", "1-2"), preserve the full range exactly
as written in the quantity field (e.g. "4-5") — do not collapse it to just one of the numbers.
If a time is only vaguely implied (not stated as a number), use null rather than guessing.
If something is not mentioned, use null. Do not invent anything.
If the text is not a recipe at all (no ingredients or cooking instructions),
return every field as null or an empty list — do not treat unrelated sentences as steps.
Reply with ONLY the JSON, nothing else, no markdown formatting.

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
webpage_import.py
pythonfrom recipe_scrapers import scrape_me
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
youtube_import.py
pythonimport yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi
from extractor import extract_recipe


def get_video_id(url):
    if "watch?v=" in url:
        return url.split("watch?v=")[1].split("&")[0]
    elif "youtu.be/" in url:
        return url.split("youtu.be/")[1].split("?")[0]
    return None


def get_title_and_description(url):
    ydl_opts = {"quiet": True, "skip_download": True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info.get("title", ""), info.get("description", ""), None
    except Exception as e:
        return "", "", str(e)


def get_transcript(video_id):
    try:
        ytt_api = YouTubeTranscriptApi()
        transcript_list = ytt_api.list(video_id)

        try:
            transcript = transcript_list.find_transcript(["en", "en-IN", "en-US", "en-GB"])
        except Exception:
            transcript = next(iter(transcript_list))
            if transcript.is_translatable and not transcript.language_code.startswith("en"):
                transcript = transcript.translate("en")

        fetched = transcript.fetch()
        full_text = " ".join(entry.text for entry in fetched)
        return full_text

    except Exception:
        return ""


def fetch_recipe_from_youtube(url):
    video_id = get_video_id(url)
    if not video_id:
        return {
            "name": None, "servings": None,
            "prep_time_minutes": None, "cook_time_minutes": None,
            "ingredients": [], "steps": [],
            "error": "Could not recognize this as a valid YouTube URL."
        }

    title, description, fetch_error = get_title_and_description(url)
    transcript = get_transcript(video_id)

    if not title and not description and not transcript:
        if fetch_error:
            lowered = fetch_error.lower()
            if "private" in lowered:
                message = "This video is private and cannot be accessed."
            elif "unavailable" in lowered or "removed" in lowered or "does not exist" in lowered:
                message = "This video is unavailable or has been removed."
            elif "age" in lowered and "restrict" in lowered:
                message = "This video is age-restricted and cannot be accessed automatically."
            elif "sign in" in lowered or "login" in lowered:
                message = "This video requires sign-in and cannot be accessed automatically."
            else:
                message = f"Could not retrieve information from this video: {fetch_error}"
        else:
            message = "Could not retrieve any information from this video."

        return {
            "name": None, "servings": None,
            "prep_time_minutes": None, "cook_time_minutes": None,
            "ingredients": [], "steps": [],
            "error": message
        }

    combined_text = f"Title: {title}\n\nDescription:\n{description}\n\nTranscript:\n{transcript}"
    structured = extract_recipe(combined_text)
    structured["name"] = structured.get("name") or title or None

    if not structured.get("steps") and not transcript:
        existing_note = structured.get("note", "") or ""
        structured["note"] = (
            existing_note + " No captions were available for this video, and the description "
            "didn't include step-by-step instructions. You may need to add the method manually."
        ).strip()

    return structured


if __name__ == "__main__":
    test_urls = [
        "https://www.youtube.com/watch?v=XxlitHO0v18",
    ]

    for url in test_urls:
        print(f"\n--- {url} ---")
        result = fetch_recipe_from_youtube(url)
        if result.get("error"):
            print(f"ERROR: {result['error']}")
        else:
            print(f"name: {result['name']}")
            print(f"ingredients: {result['ingredients']}")
            print(f"steps: {result['steps']}")
            if result.get("note"):
                print(f"NOTE: {result['note']}")
image_pdf_import.py
pythonimport os
import base64
import pytesseract
from groq import Groq
from PIL import Image, ImageOps
from pdf2image import convert_from_path
from extractor import extract_recipe, client as text_client
import cv2
import numpy as np

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

vision_client = Groq(api_key=os.environ["GROQ_API_KEY"])


def is_image_too_blurry(image_path, threshold=50):
    try:
        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            return False
        sharpness = cv2.Laplacian(img, cv2.CV_64F).var()
        return sharpness < threshold
    except Exception:
        return False


def image_to_base64(image_path):
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def extract_recipe_from_image_vision(image_path):
    try:
        base64_image = image_to_base64(image_path)

        prompt = """Look at this image of a recipe and extract all the visible text related to
the recipe: the dish name, servings, prep/cook time, every ingredient with its exact quantity
(pay close attention to fraction symbols like ½, ⅓, ¼ and ranges like 4-5 — read them precisely),
and every cooking step, in order. Transcribe only what is visibly written in the image, do not
add anything that is not there.

Do not explain your reasoning or show your thought process —
reply with ONLY the final transcribed text, nothing else."""

        response = vision_client.chat.completions.create(
            model="qwen/qwen3.6-27b",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {
                        "url": f"data:image/png;base64,{base64_image}"
                    }}
                ]
            }],
            max_tokens=4096,
            reasoning_effort="none",
            reasoning_format="hidden",
        )
        raw_output = response.choices[0].message.content

        if "<think>" in raw_output:
            if "</think>" in raw_output:
                raw_output = raw_output.split("</think>")[-1].strip()
            else:
                print("Vision response was cut off before completing.")
                return None

        return raw_output

    except Exception as e:
        print(f"Vision extraction failed: {e}")
        return None


def check_text_coherence(raw_text):
    try:
        prompt = f"""Below is text that was extracted from a photo of a recipe. Judge whether
this text is coherent, real language that makes sense, or whether it contains nonsensical,
fabricated-looking words that suggest the source was too illegible to read accurately (this can
happen with vision AI on messy handwriting).

Reply with exactly one word: COHERENT or GIBBERISH

Text to judge:
{raw_text}"""

        response = text_client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[{"role": "user", "content": prompt}],
        )
        verdict = response.choices[0].message.content.strip().upper()
        return "GIBBERISH" not in verdict

    except Exception:
        return True


def preprocess_image(image):
    image = image.convert("L")
    width, height = image.size
    image = image.resize((width * 4, height * 4), Image.LANCZOS)
    image = ImageOps.autocontrast(image)
    image = image.point(lambda x: 0 if x < 150 else 255, mode="1")
    return image


def extract_text_from_pdf(pdf_path):
    try:
        pages = convert_from_path(pdf_path)
    except Exception:
        return None

    full_text = ""
    for page_image in pages:
        page_image = preprocess_image(page_image)
        page_text = pytesseract.image_to_string(page_image, config="--psm 6")
        full_text += page_text + "\n"
    return full_text


def fetch_recipe_from_file(file_path):
    lower_path = file_path.lower()

    if lower_path.endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp")):
        if is_image_too_blurry(file_path):
            return {
                "name": None, "servings": None,
                "prep_time_minutes": None, "cook_time_minutes": None,
                "ingredients": [], "steps": [],
                "error": "This image is too blurry to read. Please try a clearer photo."
            }
        raw_text = extract_recipe_from_image_vision(file_path)
    elif lower_path.endswith(".pdf"):
        raw_text = extract_text_from_pdf(file_path)
    else:
        return {
            "name": None, "servings": None,
            "prep_time_minutes": None, "cook_time_minutes": None,
            "ingredients": [], "steps": [],
            "error": "Unsupported file type. Please upload an image (PNG/JPG) or PDF."
        }

    if raw_text is None:
        return {
            "name": None, "servings": None,
            "prep_time_minutes": None, "cook_time_minutes": None,
            "ingredients": [], "steps": [],
            "error": "Could not read this file. It may be corrupted or unsupported."
        }

    if not raw_text.strip():
        return {
            "name": None, "servings": None,
            "prep_time_minutes": None, "cook_time_minutes": None,
            "ingredients": [], "steps": [],
            "error": "No readable text could be found in this file."
        }

    if not check_text_coherence(raw_text):
        return {
            "name": None, "servings": None,
            "prep_time_minutes": None, "cook_time_minutes": None,
            "ingredients": [], "steps": [],
            "error": "This image is too unclear to read reliably (handwriting, blur, or poor "
                     "image quality). Please try a clearer photo, or enter the recipe manually."
        }

    print("----- RAW EXTRACTED TEXT -----")
    print(raw_text)
    print("-------------------------------")

    structured = extract_recipe(raw_text)
    return structured


if __name__ == "__main__":
    test_file = "image_test.png"
    result = fetch_recipe_from_file(test_file)

    if result.get("error"):
        print(f"ERROR: {result['error']}")
    else:
        print(f"name: {result['name']}")
        print(f"servings: {result['servings']}")
        print(f"ingredients: {result['ingredients']}")
        print(f"steps: {result['steps']}")
        if result.get("note"):
            print(f"NOTE: {result['note']}")
(README.md content already in repo — not duplicated here.)
Every Fix Made, With Reasoning (chronological)

Switched from Gemini to Groq — Gemini free tier had unworkable per-minute/per-day quotas
Built core extract_recipe() — reusable text→JSON extractor, used by all sources
Fixed: short steps like "done" were being dropped → added explicit "include every instruction" rule
Fixed: empty-input crash risk → guard clause + try/except, never crashes, always returns error field
Webpage: switched from raw JSON-LD parsing to recipe-scrapers library (handles site-specific quirks, avoids bot-blocking issues better)
Webpage: added safe_get() so one broken field doesn't kill the whole result
Webpage: added detection for blocked (403), not-found (404), paywalled, and collection/multi-recipe pages
YouTube: fixed youtube-transcript-api version mismatch (.fetch() on instance, not class)
YouTube: filtered conversational filler/small talk from transcripts (real fix, improved core prompt)
YouTube: added ingredient–step cross-checking (catches ingredients mentioned only in method, not list)
YouTube: fixed English-variant caption matching (en-IN etc.) + auto-translation fallback for non-English-only captions
YouTube: added specific error messages for private/unavailable/age-restricted videos (parses yt-dlp's actual error text)
YouTube: added title fallback when AI-derived name comes back empty
Core: added paywall keyword detection, long-text truncation (with note), duplicate ingredient merging, non-English translation (had to be strengthened twice — first attempt was too soft/buried in the prompt)
Core: added range preservation ("4-5" was being silently collapsed to "4")
Core: added instruction to deduplicate repeated instructions (e.g. bake time listed twice on a recipe card)
Core: switched model llama-3.3-70b-versatile → openai/gpt-oss-120b (Groq deprecated the former)
Images: major architecture change — started with Tesseract OCR, found it reliably misreads fraction symbols (½, ⅓, ¼) even after upscaling/binarization/PSM tuning; switched to a vision-capable AI model (qwen/qwen3.6-27b) instead, which reads images contextually like a human. This fixed fraction accuracy completely.
Images: fixed vision model exposing <think> reasoning in output; fixed a case where the response got cut off mid-reasoning (added max_tokens=4096, then found and used official reasoning_effort="none" + reasoning_format="hidden" params — most reliable fix)
Images: discovered the model can hallucinate plausible-sounding gibberish on illegible handwriting without flagging uncertainty, even when explicitly asked to. Self-reporting via prompt instructions proved unreliable (tested and disproven twice).
Images: final approach (user's own suggested simplification) — two independent, simple safety layers instead of chasing prompt-level self-awareness:

Blur detection (OpenCV Laplacian sharpness check) — runs before calling the vision model at all
Coherence check (separate AI call judging COHERENT vs GIBBERISH on the output) — runs after extraction, before structuring


PDFs still use Tesseract + preprocessing (upscale/grayscale/binarize/psm6) — not yet upgraded to vision-model approach, not yet re-tested since other changes

Known Limitations (honest, for the write-up)

PDF fraction accuracy likely still weak (Tesseract-based, same root issue as images had before the vision-model fix)
Paywall detection is keyword-based, won't catch every variant
On severely illegible handwriting, isolated word-level misreads can still occur that remain grammatically plausible (not caught by any check) — only mostly-gibberish results are reliably caught
No automated test suite — all testing has been manual via each file's __main__ block
Not yet wired into the provided HTML form (never received from supervisor)
No formal evaluation set/accuracy write-up compiled yet

Testing Completed

Pasted text: fractions/ranges, regional names, missing fields, non-recipe/empty input, non-English text, very long text — all covered
Webpage: clean site, blocked site (403, later succeeded — proved error handling works either way), personal blog, collection page, 404 — all covered
YouTube: full-info video, filler filtering, no captions, transcript-only, ingredients-only-in-steps, non-English + translation, English variants, invalid URL, non-recipe video, private/unavailable video — all covered
Images: clean printed recipe, clear handwriting, messy-but-legible handwriting, illegible/blurry image (proper rejection) — covered
Images — not yet tested: angled photo, multi-column layout, multi-recipe page, ingredients-only/steps-only image, non-English image, unrelated non-recipe photo, low-contrast/faded page
PDFs: not yet tested at all since the vision-model architecture change

What's Left

Finish remaining image edge-case tests (list above)
Test PDF path properly (consider whether to upgrade PDFs to vision-model approach too, given the fraction issue was PDF-relevant too)
Wire into the provided HTML interface (once received)
Build formal evaluation set (5–10 sample imports across all sources, saved) + accuracy write-up
1–2 page write-up: approach, key decisions, what worked, what to improve
Record 5–10 min demo walkthrough
Final README polish once form is wired in

## Update — Extended Image Testing Round (all 12 test types completed)

After the initial vision-model architecture fix, a full round of image edge-case testing was carried out against real and AI-generated test images, covering every type identified as worth testing. Two real bugs were found and fixed; several accuracy limitations were found and documented rather than chased further.

### Bugs found and fixed during this round

1. **False-precision invention** — the model was replacing vague source wording (e.g. "a small border") with an invented specific measurement (e.g. "3/4 inch border"). Fixed by adding an explicit instruction in `extractor.py` to preserve vague wording rather than invent numbers. Confirmed fixed on re-test.
2. **Crash on multi-recipe images** — an image containing two complete, separate recipes caused the model to return a JSON *list* of recipes instead of a single object, crashing `fetch_recipe_from_file` (`'list' object has no attribute 'get'`). Fixed with (a) an explicit "only extract the first recipe, always return a single object" prompt instruction, and (b) a defensive `isinstance(recipe_dict, list)` check in `extractor.py` that returns a clear error instead of crashing, even if the model ignores the instruction. Confirmed fixed on re-test — correctly extracted only the first recipe.

### Test results by type

| Type | Result |
|---|---|
| Clean printed recipe | Fully accurate |
| Handwritten (clear, real photo) | Fully accurate |
| Handwritten (messy, real photo, with page bleed-through) | Accurate; one technique-changing word misread ("Break" → "Separate") |
| Illegible/very blurry image | Correctly rejected via blur detection, no crash |
| Angled photo (AI-generated handwriting) | Fully accurate — confirms angle/perspective alone doesn't break extraction |
| Angled photo (real handwriting, good framing) | Fully accurate — combines real handwriting + angle successfully |
| Angled photo (real handwriting, poor framing/very small text) | Correctly rejected as unclear — validated against an image that was borderline for human readability too |
| Multi-column layout | Reading order stayed correct, no column-scrambling; surfaced the false-precision bug (see above) |
| Two recipes on one page | Surfaced and fixed the multi-recipe crash (see above); after fix, correctly extracts only the first recipe |
| Image with only steps, no ingredients list | Ingredient cross-checking (originally built for YouTube) correctly rebuilt a full 11-item ingredients list from step text alone |
| Non-English recipe image (French, real handwriting) | Fully accurate transcription and translation; correctly preserved the dish's proper name untranslated |
| Low-contrast/faded printed page | Strong overall; one likely fabricated sentence-completion on a physically obscured/cut-off phrase (see limitations) |
| Completely unrelated (non-recipe) photo | Correctly returned all-empty result, no fabrication |

### Known limitations documented (not fixed — judged as inherent model behavior, not fixable via prompting)

- **Single stylized-word misreads**: uncommon or decoratively-written words can occasionally be misread as a different plausible word (e.g. "pepperoni" → "pomegranate" in one test, → a garbled non-word → "pineapple" in another; "jumbo" initially misread as "kinda" in an earlier test before manual confirmation). Recurred across multiple unrelated images with different wrong substitutions each time — treated as a genuine, inherent vision-model limitation rather than a fixable prompt issue.
- **Obscured/cut-off phrase completion**: when part of a sentence is physically illegible or cut off (as opposed to illegible-but-present), the model can complete it with a plausible-sounding invented ending rather than truncating or flagging uncertainty (e.g. "Bake for 30-35 mins" completed with an unverifiable "or until golden" where the source was obscured at that exact point). Judged as a harder, fuzzier problem than the false-precision fix, and not solved.
- These two limitations are structurally different from earlier-fixed bugs: both produce text that remains grammatically coherent, so neither the blur check nor the coherence check can catch them. This is an honest, acknowledged gap in the current safety net.

### Status after this round
All 12 planned image test types completed. Two real bugs found and fixed. Two narrower limitations identified, tested for reproducibility (recurred across multiple images), and documented rather than chased further, given diminishing returns relative to time invested. Image extraction is considered solid and well-tested for the write-up's evaluation section.

**Next:** PDF testing (currently still using Tesseract-based OCR, not yet re-tested since the vision-model switch for images).