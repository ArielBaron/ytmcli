#!/usr/bin/env python3
import subprocess
import sys
import threading
from colorama import init, Fore, Style
import json
import os
import signal
import time

init(autoreset=True)

def get_audio_url(query, with_title=False):
    try:
        result = subprocess.run(
            ["yt-dlp", "-f", "bestaudio", "-j", f"ytsearch:{query}"],
            capture_output=True,
            text=True
        )
        info = json.loads(result.stdout)
        url = None
        title = None
        # Find bestaudio URL
        if 'formats' in info:
            for fmt in info['formats']:
                if fmt.get('acodec') != 'none' and fmt.get('vcodec') == 'none':
                    url = fmt.get('url')
                    break
        # Get title
        if with_title:
            title = info.get('title')
        if not url:
            print("No URL found.")
            return (None, title) if with_title else None
        return (url, title) if with_title else url
    except Exception as e:
        print(f"Error getting URL: {e}")
        return (None, None) if with_title else None

def start_vlc(url):
    return subprocess.Popen(
        ["cvlc", "--play-and-exit", "--quiet", url],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

def force_kill_vlc(vlc_proc):
    """Kill VLC process with escalating force"""
    # First try terminate (SIGTERM)
    vlc_proc.terminate()
        
       

def monitor_quit(vlc_proc):
    while True:
        try:
            key = input()
            if key.strip().lower() == "q":
                force_kill_vlc(vlc_proc)
                os._exit(0)  # Force exit the entire program
        except KeyboardInterrupt:
            force_kill_vlc(vlc_proc)
            os._exit(0)

def handle_playback(vlc_proc):
    # Set up signal handlers for Ctrl+C
    def signal_handler(sig, frame):
        force_kill_vlc(vlc_proc)
        os._exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start quit monitor thread
    quit_thread = threading.Thread(target=monitor_quit, args=(vlc_proc,), daemon=True)
    quit_thread.start()
    
    # Wait for VLC to finish or be killed
    try:
        vlc_proc.wait()
    except KeyboardInterrupt:
        force_kill_vlc(vlc_proc)
        os._exit(0)

def play(is_cli, *args):
    if not is_cli:
        query = " ".join(args)
        url = get_audio_url(query)
        if not url:
            return 1
        vlc_proc = start_vlc(url)
        handle_playback(vlc_proc)
    
    if is_cli:
        print(Fore.CYAN + Style.BRIGHT + "♫ YTMCLI - YouTube Music CLI")
        print(Fore.MAGENTA + "----------------------------------")
        print(Fore.CYAN + "Press 'q' + Enter to quit, or Ctrl+C")
        query = input(Fore.YELLOW + Style.BRIGHT + "♫ Enter song > " + Style.RESET_ALL)
        url, title = get_audio_url(query, with_title=True)
        if not url:
            return 1
        if title:
            print(Fore.GREEN + Style.BRIGHT + f"Title: {title}")
        vlc_proc = start_vlc(url)
        handle_playback(vlc_proc)

if __name__ == "__main__":
    is_cli = len(sys.argv) == 1
    play(is_cli, *sys.argv[1:])