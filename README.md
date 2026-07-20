# Smart Recipe Import

A feature that automatically extracts recipe information from a webpage link, a YouTube video, an uploaded image/PDF, or pasted text — and structures it into clean fields (name, servings, ingredients, steps, etc.) ready to populate a recipe form.

Built as part of the ShopConnect AI/Software Engineering internship project.

## Status

**In progress.** Core extraction pipeline is built and tested for all four source types. Not yet wired into the provided HTML interface (pending receipt of that file). See "What's Done" and "What's Left" below.

## How It Works

All four source types funnel into one shared extraction core, `extractor.py`, which turns messy raw text into clean structured JSON using an LLM (Groq/Llama). Each source type is responsible only for getting usable text *out* of its source — the cleanup logic itself is never duplicated.
Pasted text ─────────────────┐
Webpage (scraped)  ──────────┼──► extract_recipe() ──► structured JSON ──► (form, pending)
YouTube (title+desc+transcript)┤
Image/PDF (vision AI / OCR) ─┘

## Files

| File | Purpose |
|---|---|
| `extractor.py` | Core: takes any messy text, returns structured recipe JSON. Used by every other file. |
| `webpage_import.py` | Given a recipe URL, scrapes the page and extracts a recipe. |
| `youtube_import.py` | Given a YouTube URL, gathers title/description/transcript and extracts a recipe. |
| `image_pdf_import.py` | Given an image or PDF file, reads its contents and extracts a recipe. |

## Setup

### Requirements
- Python 3.10+
- A [Groq API key](https://console.groq.com) (free tier)
- [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) installed and on your system PATH (used for PDF reading)
- [Poppler](https://github.com/oschwartz10612/poppler-windows/releases) installed and on your system PATH (required by `pdf2image` for PDFs)

### Install Python dependencies
```bash
pip install groq requests beautifulsoup4 recipe-scrapers yt-dlp youtube-transcript-api pytesseract pillow pdf2image
```

### Set your API key
Set an environment variable named `GROQ_API_KEY` with your Groq API key.

Windows (Command Prompt):
setx GROQ_API_KEY "your-key-here"
Then close and reopen your terminal.

### Tesseract path (Windows only)
`image_pdf_import.py` points directly to the Tesseract executable. Update this line if your install path differs:
```python
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
```

## Running

Each file can be run directly to test its extraction logic against sample inputs defined at the bottom of the file:

```bash
python extractor.py          # test pasted-text extraction
python webpage_import.py     # test webpage extraction against sample URLs
python youtube_import.py     # test YouTube extraction against a sample video
python image_pdf_import.py   # test image/PDF extraction against a sample file
```

## Tools Used, and Why

- **Groq (Llama 3.3 / Qwen vision model)** — free-tier LLM API for text cleanup and image understanding. Chosen after hitting persistent quota limits on Gemini's free tier.
- **`recipe-scrapers`** — open-source library that reliably extracts structured recipe data from hundreds of recipe websites, handling site-specific quirks internally.
- **`yt-dlp`** — fetches YouTube video metadata (title, description) without requiring an official API key.
- **`youtube-transcript-api`** — fetches video captions/transcripts, with support for language selection and auto-translation.
- **Vision AI model (via Groq)** — used for reading recipe images directly, after finding that traditional OCR (Tesseract) could not reliably read fraction symbols (½, ⅓, ¼) in ingredient quantities.
- **Tesseract + Poppler** — used for PDF text extraction (converts PDF pages to images, then reads them).

## What's Done

- * *Pasted text**: full extraction pipeline, tested against messy/incomplete input, non-recipe input, ranges/fractions, regional ingredient names, non-English text, and very long text (with safe truncation).
- **Webpages**: scraping via `recipe-scrapers`, with graceful handling of blocked sites (403), missing pages (404), paywalls, timeouts, multi-recipe collection pages, and messy personal-blog layouts.
- **YouTube**: combines title, description, and transcript; filters conversational filler from transcripts; cross-checks ingredients mentioned only in steps; handles missing captions, non-English audio (with auto-translation), private/unavailable videos, and invalid URLs.
- **Images**: uses a vision AI model to read recipe images directly, correctly handling fraction quantities (an area where traditional OCR failed).
- **Shared behavior across all sources**: never crashes (all failures return a clear `error` or `note` field), never invents data for missing fields, duplicate ingredients are merged.

## What's Left / Known Limitations

- PDF extraction still uses traditional OCR (Tesseract), not yet upgraded to the vision-model approach used for images — fraction accuracy in PDFs is untested/likely weaker.
- Broader image edge cases (handwritten recipes, multi-recipe pages, non-English images, non-recipe images) are being tested next.
- Not yet wired into the provided HTML interface.
- Paywall detection on webpages is keyword-based and may not catch every paywall variant.
- No automated test suite yet — testing has been manual, using sample inputs in each file's `__main__` block.
- Evaluation set and formal accuracy write-up not yet compiled.

## Sample Results

*(To be added: 5–10 example imports across all source types, saved for review.)*