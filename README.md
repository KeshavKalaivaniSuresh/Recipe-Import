# Smart Recipe Import

A feature that automatically extracts recipe information from a webpage link, a YouTube video, an uploaded image/PDF, or pasted text — and structures it into clean fields (name, servings, ingredients, steps, etc.) ready to populate a recipe form.

Built as part of the ShopConnect AI/Software Engineering internship project.

## Status

**In progress.** Core extraction pipeline is built and thoroughly tested for all four source types, including extensive edge-case testing (24+ distinct real-world conditions across images and PDFs alone). Not yet wired into the provided HTML interface (pending receipt of that file from supervisor).

## How It Works

All four source types funnel into one shared extraction core, `extractor.py`, which turns messy raw text into clean structured JSON using an LLM (Groq). Each source type is responsible only for getting usable text *out* of its source — the cleanup logic itself is never duplicated.

Pasted text ─────────────────┐
Webpage (scraped) ──────────┼──► extract_recipe() ──► structured JSON ──► (form, pending)
YouTube (title+desc+transcript)┤
Image/PDF (vision AI, both use the same approach) ─┘


## Files

| File | Purpose |
|---|---|
| `extractor.py` | Core: takes any messy text, returns structured recipe JSON. Used by every other file. |
| `webpage_import.py` | Given a recipe URL, scrapes the page and extracts a recipe. |
| `youtube_import.py` | Given a YouTube URL, gathers title/description/transcript and extracts a recipe. |
| `image_pdf_import.py` | Given an image or PDF file, reads its contents (via vision AI) and extracts a recipe. |

## Setup

### Requirements
- Python 3.10+
- A [Groq API key](https://console.groq.com) (free tier)
- [Poppler](https://github.com/oschwartz10612/poppler-windows/releases) installed and on your system PATH (required by `pdf2image` to convert PDF pages to images)

### Install Python dependencies
```bash
pip install groq requests beautifulsoup4 recipe-scrapers yt-dlp youtube-transcript-api pillow pdf2image opencv-python
```

### Set your API key
Set an environment variable named `GROQ_API_KEY` with your Groq API key.

Windows (Command Prompt):

setx GROQ_API_KEY "your-key-here"

Then close and reopen your terminal.

## Running

Each file can be run directly to test its extraction logic against sample inputs defined at the bottom of the file:

```bash
python extractor.py          # test pasted-text extraction
python webpage_import.py     # test webpage extraction against sample URLs
python youtube_import.py     # test YouTube extraction against a sample video
python image_pdf_import.py   # test image/PDF extraction against a sample file
```

## Tools Used, and Why

- **Groq (`openai/gpt-oss-120b` for text, `qwen/qwen3.6-27b` for vision)** — free-tier LLM API for text cleanup and image/PDF understanding. Chosen after hitting persistent quota limits on Gemini's free tier. Switched away from `llama-3.3-70b-versatile` after Groq deprecated it.
- **`recipe-scrapers`** — open-source library that reliably extracts structured recipe data from hundreds of recipe websites, handling site-specific quirks internally.
- **`yt-dlp`** — fetches YouTube video metadata (title, description) without requiring an official API key.
- **`youtube-transcript-api`** — fetches video captions/transcripts, with support for language selection and auto-translation.
- **Vision AI model (via Groq)** — used for reading both recipe images and PDF pages directly, after finding that traditional OCR (Tesseract) could not reliably read fraction symbols (½, ⅓, ¼) in ingredient quantities. This was tested and confirmed as a genuine OCR limitation (not fixable via image preprocessing) before switching architectures.
- **`pdf2image` + Poppler** — converts PDF pages into images so the same vision-based reading approach used for photos can be applied to PDFs too.
- **OpenCV** — used for a simple sharpness check to detect and reject blurry images before wasting an API call on them.

## What's Done

- **Pasted text**: full extraction pipeline, tested against messy/incomplete input, non-recipe input, ranges/fractions, regional ingredient names, non-English text, very long text (with safe truncation), and multi-recipe sources.
- **Webpages**: scraping via `recipe-scrapers`, with graceful handling of blocked sites (403), missing pages (404), paywalls, timeouts, and multi-recipe collection pages.
- **YouTube**: combines title, description, and transcript; filters conversational filler; cross-checks ingredients mentioned only in steps; handles missing captions, non-English audio (with auto-translation), private/unavailable videos, and invalid URLs.
- **Images**: uses a vision AI model to read recipe images directly. Tested across 12 distinct conditions — clean and handwritten recipes (including real, messy handwriting), illegible/blurry images (correctly rejected), angled photos, multi-column layouts, multi-recipe pages, ingredients-only-in-steps, non-English images, faded/low-contrast pages, and unrelated non-recipe photos.
- **PDFs**: upgraded to the same vision-model approach as images. Tested across 9 distinct conditions — normal and dense/long recipes, password-protected files, corrupted files, merged/multi-recipe content, scanned vs. digital-native PDFs, rotated pages, and PDFs with very large embedded images.
- **Shared safety behavior across all sources**: never crashes (all failures return a clear `error` or `note` field), never invents data for missing fields, duplicate ingredients merged, vague source wording preserved rather than replaced with invented precise numbers, multi-recipe sources handled without crashing.

## What's Left / Known Limitations

- Additional file format support (`.txt`, `.heic` for iPhone photos, etc.) — currently only PDF and common image formats (PNG/JPG/JPEG/WEBP/BMP) are supported, matching the project's stated requirements; `.heic` support is a realistic gap worth considering given how common iPhone photos are.
- Not yet wired into the provided HTML interface.
- Paywall detection on webpages is keyword-based and may not catch every paywall variant.
- On severely illegible handwriting or images, isolated single-word misreads can occasionally occur that remain grammatically plausible and aren't caught by any safety check (documented, not fixable via prompting alone).
- On text that is physically obscured or cut off (as opposed to illegible-but-present), the model can occasionally complete a partial phrase with a plausible-sounding but unverifiable ending.
- No automated test suite — all testing has been extensive but manual, via each file's `__main__` block.
- Evaluation set and formal accuracy write-up not yet compiled.

## Sample Results

*(To be added: 5–10 example imports across all source types, saved for review.)*


## Recent Updates
- Added support for HEIC/HEIF image uploads (Apple's default photo format), converted internally to JPEG before processing.
- Fixed image uploads being incorrectly labeled as PNG regardless of their actual file type.
- Improved PDF processing performance by removing a redundant conversion step.
- Fixed a bug where valid, normal-sized recipes could incorrectly return a "recipe too large" error due to a missing model configuration setting.