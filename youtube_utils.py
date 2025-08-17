import subprocess
import json

def get_audio_url(query, with_title=False, with_duration=False):
    try:
        # Debug: Print the command being run
        cmd = ["yt-dlp", "--extractor-args", "youtube:player_client=android", "-f", "bestaudio", "-j", f"ytsearch:{query}"]
        print(f"Debug: Running command: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )
        
        # Debug: Print the return code and any error output
        print(f"Debug: Command returned code: {result.returncode}")
        if result.stderr:
            print(f"Debug: Error output: {result.stderr}")
        
        if not result.stdout.strip():
            print("Error: Empty response from yt-dlp")
            if with_title and with_duration:
                return (None, None, None)
            elif with_title:
                return (None, None)
            elif with_duration:
                return (None, None)
            else:
                return None
            
        info = json.loads(result.stdout)
        url = None
        title = None
        duration = None

        if 'formats' in info:
            for fmt in info['formats']:
                if fmt.get('acodec') != 'none' and fmt.get('vcodec') == 'none':
                    url = fmt.get('url')
                    break

        if with_title:
            title = info.get('title')
        if with_duration:
            duration = info.get('duration')

        if not url:
            print("No URL found.")
            if with_title and with_duration:
                return (None, title, duration)
            elif with_title:
                return (None, title)
            elif with_duration:
                return (None, duration)
            else:
                return None

        if with_title and with_duration:
            return (url, title, duration)
        elif with_title:
            return (url, title)
        elif with_duration:
            return (url, duration)
        else:
            return url

    except json.JSONDecodeError as e:
        print(f"JSON Parse Error: {e}")
        print(f"Raw output from yt-dlp: {result.stdout}")
        print(f"Error output from yt-dlp: {result.stderr}")
        if with_title and with_duration:
            return (None, None, None)
        elif with_title:
            return (None, None)
        elif with_duration:
            return (None, None)
        else:
            return None
    except Exception as e:
        print(f"Error getting URL: {e}")
        if with_title and with_duration:
            return (None, None, None)
        elif with_title:
            return (None, None)
        elif with_duration:
            return (None, None)
        else:
            return None
