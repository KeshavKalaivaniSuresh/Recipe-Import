import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi
from extractor import extract_recipe


def get_video_id(url):
    """Extract the video ID from a YouTube URL."""
    if "watch?v=" in url:
        return url.split("watch?v=")[1].split("&")[0]
    elif "youtu.be/" in url:
        return url.split("youtu.be/")[1].split("?")[0]
    return None


def get_title_and_description(url):
    """Use yt-dlp to fetch just metadata, without downloading the video."""
    ydl_opts = {"quiet": True, "skip_download": True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info.get("title", ""), info.get("description", "")
    except Exception as e:
        print(f"Could not fetch video metadata: {e}")
        return "", ""


def get_transcript(video_id):
    """Try to fetch an English transcript. Falls back to translating a foreign one if needed."""
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
    """
    Given a YouTube video URL, gather title, description, and transcript,
    then extract a structured recipe from the combined text.
    """
    video_id = get_video_id(url)
    if not video_id:
        return {
            "name": None, "servings": None,
            "prep_time_minutes": None, "cook_time_minutes": None,
            "ingredients": [], "steps": [],
            "error": "Could not recognize this as a valid YouTube URL."
        }

    title, description = get_title_and_description(url)
    transcript = get_transcript(video_id)

    if not title and not description and not transcript:
        return {
            "name": None, "servings": None,
            "prep_time_minutes": None, "cook_time_minutes": None,
            "ingredients": [], "steps": [],
            "error": "Could not retrieve any information from this video."
        }

    combined_text = f"Title: {title}\n\nDescription:\n{description}\n\nTranscript:\n{transcript}"
    structured = extract_recipe(combined_text)
    structured["name"] = structured.get("name") or title or None

    if not structured.get("steps") and not transcript:
        structured["note"] = (
            "No captions were available for this video, and the description didn't include "
            "step-by-step instructions. You may need to add the method manually."
        )

    return structured


if __name__ == "__main__":
    test_urls = [
        "https://www.youtube.com/watch?v=GdxdfME7VY4",
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