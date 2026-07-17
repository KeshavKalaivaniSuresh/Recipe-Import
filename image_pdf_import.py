import os
import base64
from groq import Groq
from PIL import Image
from pdf2image import convert_from_path
from extractor import extract_recipe, client as text_client
import cv2
import numpy as np
import tempfile


vision_client = Groq(api_key=os.environ["GROQ_API_KEY"])


def is_image_too_blurry(image_path, threshold=50):
    """Measure image sharpness. Low values indicate a blurry image."""
    try:
        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            return False  # let the normal error handling deal with unreadable files
        sharpness = cv2.Laplacian(img, cv2.CV_64F).var()
        return sharpness < threshold
    except Exception:
        return False  # if the check itself fails, don't block a possibly-good image


def image_to_base64(image_path):
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def extract_recipe_from_image_vision(image_path):
    """Use a vision-capable AI model to directly read a recipe image."""
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
        finish_reason = response.choices[0].finish_reason

        if finish_reason == "length":
            print("Vision response was cut off due to length — content may be incomplete.")
            return None

        # Strip any internal reasoning block the model may include
        if "<think>" in raw_output:
            if "</think>" in raw_output:
                raw_output = raw_output.split("</think>")[-1].strip()
            else:
                # Response was cut off mid-reasoning before finishing — not safe to use
                print("Vision response was cut off before completing.")
                return None

        return raw_output

    except Exception as e:
        print(f"Vision extraction failed: {e}")
        return None


def check_text_coherence(raw_text):
    """
    Ask an AI model to independently judge whether the extracted text is coherent,
    real language, or likely fabricated/gibberish from a misread illegible source.
    Returns True if the text looks reliable, False if it looks like gibberish.
    """
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
            max_tokens=8192,
            reasoning_effort="none",
        )
        verdict = response.choices[0].message.content.strip().upper()
        return "GIBBERISH" not in verdict

    except Exception:
        return True  # if the check itself fails, don't block a possibly-good result


def extract_text_from_pdf(pdf_path):
    """Convert each PDF page to an image, then use the vision model to read each page."""
    try:
        pages = convert_from_path(pdf_path)
    except Exception:
        return None

    full_text = ""
    for i, page_image in enumerate(pages):
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            page_image.save(tmp.name, "PNG")
            page_text = extract_recipe_from_image_vision(tmp.name)
            if page_text:
                full_text += page_text + "\n"

    return full_text if full_text.strip() else None


def fetch_recipe_from_file(file_path):
    """
    Given a path to an image or PDF file, extract raw text,
    then extract a structured recipe from it.
    """
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
        try:
            pages = convert_from_path(file_path)
            if len(pages) > 3:
                return {
                    "name": None, "servings": None,
                    "prep_time_minutes": None, "cook_time_minutes": None,
                    "ingredients": [], "steps": [],
                    "error": (
                        "This PDF is too long or detailed to process reliably. To fix this:\n"
                        "1. Upload a shorter recipe (3 pages or fewer)\n"
                        "2. Remove any extra pages that aren't part of the recipe itself "
                        "(e.g. photos, notes, or ads)\n"
                        "3. Or copy the recipe text and paste it in directly instead of "
                        "uploading the file"
                    )
                }
        except Exception as e:
            error_text = str(e).lower()
            if "password" in error_text or "encrypt" in error_text:
                return {
                    "name": None, "servings": None,
                    "prep_time_minutes": None, "cook_time_minutes": None,
                    "ingredients": [], "steps": [],
                    "error": "This PDF is password-protected. Please remove the password "
                             "and upload it again, or paste the recipe text instead."
                }
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
            "error": "This file is too unclear to read reliably (handwriting, blur, or poor "
                     "file quality). Please try a clearer file, or enter the recipe manually."
        }

    print("----- RAW EXTRACTED TEXT -----")
    print(raw_text)
    print("-------------------------------")

    structured = extract_recipe(raw_text)
    return structured


if __name__ == "__main__":
    test_file = "PDF_Tests/high_embedded-pixeled_pdf_test.pdf"
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