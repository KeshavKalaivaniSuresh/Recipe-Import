import os
import base64
import pytesseract
from groq import Groq
from PIL import Image, ImageOps
from pdf2image import convert_from_path
from extractor import extract_recipe, client as text_client
import cv2
import numpy as np

# Windows-specific: tell pytesseract exactly where tesseract.exe is (still used for PDFs)
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

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
        )
        verdict = response.choices[0].message.content.strip().upper()
        return "GIBBERISH" not in verdict

    except Exception:
        return True  # if the check itself fails, don't block a possibly-good result


def preprocess_image(image):
    """Improve image quality for better OCR accuracy (used for PDFs)."""
    image = image.convert("L")
    width, height = image.size
    image = image.resize((width * 4, height * 4), Image.LANCZOS)
    image = ImageOps.autocontrast(image)
    image = image.point(lambda x: 0 if x < 150 else 255, mode="1")
    return image


def extract_text_from_pdf(pdf_path):
    """Convert each PDF page to an image, then run OCR on each page."""
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
    test_file = "bad_multi-layout_image_test.png"
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