#!/usr/bin/env python3
import subprocess
import sys
import threading
from colorama import init, Fore, Style
init(autoreset=True)

def get_audio_url(query):
    try:
        result = subprocess.run(
            ["yt-dlp", "-f", "bestaudio", "-g", f"ytsearch:{query}"],
            capture_output=True,
            text=True
        )
        url = result.stdout.strip()
        if not url:
            print("No URL found.")
            return None
        return url
    except Exception as e:
        print(f"Error getting URL: {e}")
        return None

def start_vlc(url):
    return subprocess.Popen(
        ["cvlc", "--play-and-exit", "--quiet", url],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

def monitor_quit(vlc_proc):
    while True:
        key = input()
        if key.strip().lower() == "q":
            vlc_proc.terminate()
            break

def handle_playback(vlc_proc):
    threading.Thread(target=monitor_quit, args=(vlc_proc,), daemon=True).start()

def play(is_cli,*args):
    if not is_cli:
        query = " ".join(args)
        url = get_audio_url(query)
        vlc_proc = start_vlc(url)
        handle_playback(vlc_proc)
        if not url:
            return 1
    if is_cli:
        print(Fore.CYAN + Style.BRIGHT + "♫ YTMCLI - YouTube Music CLI")
        print(Fore.MAGENTA + "----------------------------------")
        query = input(Fore.YELLOW + Style.BRIGHT + "♫ Enter song > " + Style.RESET_ALL)
        url = get_audio_url(query)
        vlc_proc = start_vlc(url)
        handle_playback(vlc_proc)
        if not url:
            return 1

if __name__ == "__main__":
    # CLI prompt logic is kept outside the play function so play() can be used directly in scripts or automation without user interaction.
    is_cli = len(sys.argv) == 1
    play(is_cli,*sys.argv[1:])
