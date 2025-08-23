#!/usr/bin/env python3
import sys
import threading
import random
from colorama import init, Fore, Style
from get_audio_url import get_audio_url
from vlc_client import start_vlc, force_kill_vlc
from screen import draw_screen
from history import YTMCLIHistory

init(autoreset=True)

def handle_playback(vlc_proc, title=None):
    """
    Starts the visualizer thread and waits for VLC playback. abc
    Returns True if playback was stopped by user (q or Ctrl+C), False otherwise.
    """
    stopped_by_user = False

    def screen_runner():
        nonlocal stopped_by_user
        try:
            error = draw_screen(vlc_proc, title)
        except KeyboardInterrupt:
            stopped_by_user = True
        
        stopped_by_user = error == 'quit'
    screen_thread = threading.Thread(target=screen_runner)
    screen_thread.start()

    try:
        vlc_proc.wait()
    except KeyboardInterrupt:
        force_kill_vlc(vlc_proc)
        stopped_by_user = True
    finally:
        if screen_thread.is_alive():
            screen_thread.join()

    return stopped_by_user

def resolve_special_query(query: str, history: YTMCLIHistory):
    entries = history.all()
    if not query.startswith(":") or not entries:
        return query

    cmd = query[1:]

    if cmd == "r":
        return random.choice(entries)

    if cmd == "l":
        for i, entry in enumerate(entries[-20:][::-1], 1):
            print(f"{i}: {entry}")
        return None

    if cmd == "h":
        print(Fore.CYAN + Style.BRIGHT + "Available commands:")
        print(Fore.YELLOW + ":r" + Style.RESET_ALL + " - Play a random song from history")
        print(Fore.YELLOW + ":l" + Style.RESET_ALL + " - List last 20 history entries")
        print(Fore.YELLOW + ":<number>" + Style.RESET_ALL + " - Play the nth last entry from history")
        print(Fore.YELLOW + ":h" + Style.RESET_ALL + " - Show this help message")
        return None

    if cmd.isdigit():
        n = int(cmd)
        if 1 <= n <= len(entries):
            return entries[-n]

    return query

def play(is_cli, *args):
    history = YTMCLIHistory()

    if not is_cli:
        query = " ".join(args)
        query = resolve_special_query(query, history)
        if not query:
            return
        url = get_audio_url(query)
        if url:
            history.add(query)
            handle_playback(start_vlc(url))
        return

    print(Fore.CYAN + Style.BRIGHT + "♫ YTMCLI - YouTube Music CLI")
    print(Fore.MAGENTA + "----------------------------------")
    print(Fore.CYAN + "Press 'q' to quit, or Ctrl+C")

    while True:
        try:
            query = input(Fore.YELLOW + Style.BRIGHT + "♫ Enter song > " + Style.RESET_ALL)
        except (EOFError, ValueError, KeyboardInterrupt):
            print()
            break

        if query.lower() == "q":
            break

        query = resolve_special_query(query, history)
        if not query:
            continue  # special command handled

        try:
            url, title, _ = get_audio_url(query, with_title=True, with_duration=True)
        except Exception as e:
            print(Fore.RED + f"Error getting audio: {e}")
            continue

        if url:
            history.add(query)
            stopped = handle_playback(start_vlc(url), title)
            if stopped:
                sys.exit(0)
                exit()
                quit()

if __name__ == "__main__":
    is_cli = (len(sys.argv) == 1)
    play(is_cli, *sys.argv[1:])
