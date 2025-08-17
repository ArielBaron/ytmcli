#!/usr/bin/env python3
import subprocess
import json

# --------------------------------------------------
# YouTube URL fetching (search → bestaudio URL (+ title/duration))
# --------------------------------------------------
def get_audio_url(query, with_title=False, with_duration=False):
    """
    Runs yt-dlp with android_music extractor and returns a tuple:
      (url, title, duration)
    Any of title/duration will be None if not requested.
    """
    try:
        result = subprocess.run(
            ["yt-dlp", "--extractor-args", "youtube:player_client=android_music",
             "-f", "bestaudio", "-j", f"ytsearch:{query}"],
            capture_output=True, text=True
        )
        info = json.loads(result.stdout or "null")

        if not info:
            return (None, None, None) if (with_title or with_duration) else None

        url = None
        for fmt in info.get('formats', []):
            if fmt.get('acodec') != 'none' and fmt.get('vcodec') == 'none':
                url = fmt.get('url')
                break

        title = info.get('title') if with_title else None
        duration = info.get('duration') if with_duration else None

        if not url:
            return (None, title, duration) if (with_title or with_duration) else None

        if with_title and with_duration:
            return (url, title, duration)
        if with_title:
            return (url, title)
        if with_duration:
            return (url, duration)
        return url

    except Exception:
        if with_title and with_duration:
            return (None, None, None)
        if with_title or with_duration:
            return (None, None)
        return None
