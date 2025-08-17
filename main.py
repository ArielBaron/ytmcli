#!/usr/bin/env python3
import sys
import threading
import random
from colorama import init, Fore, Style
from get_audio_url  import get_audio_url
from vlc_client import start_vlc, force_kill_vlc
from screen import draw_screen

init(autoreset=True)

def handle_playback(vlc_proc, title=None):
    screen_thread = threading.Thread(target=draw_screen, args=(vlc_proc, title), daemon=True)
    screen_thread.start()
    try:
        vlc_proc.wait()
    except KeyboardInterrupt:
        force_kill_vlc(vlc_proc)

def play(is_cli, *args):
    if not is_cli:
        query = " ".join(args)
        if query == ":r":
            query = random.choice([
                "https://www.youtube.com/watch?v=482tDopNzoc",
                "https://www.youtube.com/watch?v=uaFzmZrKKKw",
                "https://www.youtube.com/watch?v=7qqcZIHxyRI",
                "https://www.youtube.com/watch?v=Cr4gKVsqh9o",
                "https://www.youtube.com/watch?v=TnRZhLRv6eM"
            ])
        url = get_audio_url(query)
        if url:
            handle_playback(start_vlc(url))
        return

    print(Fore.CYAN + Style.BRIGHT + "♫ YTMCLI - YouTube Music CLI")
    print(Fore.MAGENTA + "----------------------------------")
    print(Fore.CYAN + "Press 'q' to quit, or Ctrl+C")
    query = input(Fore.YELLOW + Style.BRIGHT + "♫ Enter song > " + Style.RESET_ALL)

    if query == ":r":
        query = random.choice([
            "https://www.youtube.com/watch?v=482tDopNzoc",
            "https://www.youtube.com/watch?v=uaFzmZrKKKw",
            "https://www.youtube.com/watch?v=7qqcZIHxyRI",
            "https://www.youtube.com/watch?v=Cr4gKVsqh9o",
            "https://www.youtube.com/watch?v=TnRZhLRv6eM"
        ])

    url, title, _ = get_audio_url(query, with_title=True, with_duration=True)
    if url:
        handle_playback(start_vlc(url), title)

if __name__ == "__main__":
    is_cli = (len(sys.argv) == 1)
    play(is_cli, *sys.argv[1:])
