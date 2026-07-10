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
    """Try to fetch captions/transcript text. Returns empty string if unavailable."""
    try:
        ytt_api = YouTubeTranscriptApi()
        transcript_list = ytt_api.fetch(video_id)
        full_text = " ".join(entry.text for entry in transcript_list)
        return full_text
    except Exception as e:
        print(f"No transcript available: {e}")
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
    return structured


if __name__ == "__main__":
    test_url = "https://www.youtube.com/watch?v=XxlitHO0v18"
    result = fetch_recipe_from_youtube(test_url)

    if result.get("error"):
        print(f"ERROR: {result['error']}")
    else:
        print(f"name: {result['name']}")
        print(f"servings: {result['servings']}")
        print(f"ingredients: {result['ingredients']}")
        print(f"steps: {result['steps']}")