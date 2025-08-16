#!/usr/bin/env python3
import subprocess
import sys
import threading
from colorama import init, Fore, Style
init(autoreset=True)

import json
import os
import signal

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

def monitor_quit(vlc_proc):
    while True:
        key = input()
        if key.strip().lower() == "q":
            vlc_proc.terminate()
            try:
                vlc_proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                vlc_proc.kill()
            # Fallback: kill all cvlc and vlc processes
            subprocess.run(["pkill", "-9", "cvlc"])
            subprocess.run(["pkill", "-9", "vlc"])
            subprocess.run(["killall", "-9", "cvlc"])
            subprocess.run(["killall", "-9", "vlc"])
            # Extreme fallback: scan all processes and kill any with 'vlc' or 'cvlc' in their cmdline
            try:
                import psutil
            except ImportError:
                subprocess.run([sys.executable, "-m", "pip", "install", "psutil"])
                import psutil
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = ' '.join(proc.info.get('cmdline', []))
                    if 'vlc' in cmdline or 'cvlc' in cmdline:
                        os.kill(proc.info['pid'], signal.SIGKILL)
                except Exception:
                    pass
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
        url, title = get_audio_url(query, with_title=True)
        if title:
            print(Fore.GREEN + Style.BRIGHT + f"Title: {title}")
        vlc_proc = start_vlc(url)
        handle_playback(vlc_proc)
        if not url:
            return 1

if __name__ == "__main__":
    # CLI prompt logic is kept outside the play function so play() can be used directly in scripts or automation without user interaction.
    is_cli = len(sys.argv) == 1
    play(is_cli,*sys.argv[1:])
