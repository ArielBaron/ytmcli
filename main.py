#!/usr/bin/env python3
import subprocess
import sys
import threading
from colorama import init, Fore, Style
import json
import os
import signal
import time
import tty
import termios
import select
import random
init(autoreset=True)

# -----------------------------
# YouTube URL fetching
# -----------------------------
def get_audio_url(query, with_title=False, with_duration=False):
    try:
        result = subprocess.run(
            ["yt-dlp", "-f", "bestaudio", "-j", f"ytsearch:{query}"],
            capture_output=True,
            text=True
        )
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

# -----------------------------
# VLC Control
# -----------------------------
def start_vlc(url):
    """Start VLC with RC interface"""
    return subprocess.Popen(
        ["cvlc", "--play-and-exit", "--quiet", "--extraintf", "rc", url],
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True
    )

def force_kill_vlc(vlc_proc):
    if vlc_proc.poll() is None:
        vlc_proc.terminate()

def control_vlc(vlc_proc, action):
    """Send RC commands to running VLC"""
    if not vlc_proc or vlc_proc.poll() is not None:
        return
    cmd = ""
    if action == 'pause':
        cmd = "pause\n"
    elif action == 'volume_up':
        cmd = "volup 1\n"
    elif action == 'volume_down':
        cmd = "voldown 1\n"
    elif action == 'forward':
        cmd = "seek +5\n"
    elif action == 'backward':
        cmd = "seek -5\n"
    
    if cmd:
        vlc_proc.stdin.write(cmd)
        vlc_proc.stdin.flush()

# -----------------------------
# Input / Screen
# -----------------------------
def display_progress(duration, elapsed, percent):
    bar_length = 30
    exact_position = bar_length * percent / 100
    whole_part = int(exact_position)
    fractional_part = exact_position - whole_part
    bar = '█' * whole_part

    if fractional_part > 0:
        if fractional_part <= 0.125: bar += ' '
        elif fractional_part <= 0.25: bar += '▏'
        elif fractional_part <= 0.375: bar += '▎'
        elif fractional_part <= 0.5: bar += '▍'
        elif fractional_part <= 0.625: bar += '▌'
        elif fractional_part <= 0.75: bar += '▋'
        elif fractional_part <= 0.875: bar += '▊'
        else: bar += '▉'

    remaining_length = bar_length - len(bar)
    if remaining_length > 0:
        bar += ' ' * remaining_length

    elapsed_min, elapsed_sec = divmod(int(elapsed), 60)
    duration_min, duration_sec = divmod(int(duration), 60) if duration else (0,0)
    remaining = max(0, duration - elapsed)
    remaining_min, remaining_sec = divmod(int(remaining), 60)

    print(f'[{bar}] {elapsed_min:02d}:{elapsed_sec:02d} / {duration_min:02d}:{duration_sec:02d} '
          f'[{percent:.1f}%] [{remaining_min:02d}:{remaining_sec:02d} remaining]')

def display_controls():
    controls = [
        "Press i to increase volume",
        "Press o to decrease volume",
        "Press l to move forwards 5s",
        "Press k to move backwards 5s",
        "Press p to pause/unpause",
        "Press q to quit"
    ]
    return "\n".join(controls)

def draw_screen(vlc_proc, duration, title):
    start_time = time.time()
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    tty.setcbreak(fd)

    try:
        while vlc_proc.poll() is None:
            elapsed = time.time() - start_time
            percent = min(100, (elapsed / duration * 100)) if duration else 0

            sys.stdout.write('\033[2J\033[H')  # Clear screen
            if title:
                print(Fore.GREEN + Style.BRIGHT + f"Title: {title}\n")
            display_progress(duration, elapsed, percent)
            print(display_controls())
            sys.stdout.flush()
            time.sleep(0.1)

            if select.select([sys.stdin], [], [], 0)[0]:
                key = sys.stdin.read(1).lower()
                if key == 'q':
                    force_kill_vlc(vlc_proc)
                    os._exit(0)
                elif key == 'i':
                    control_vlc(vlc_proc, 'volume_up')
                elif key == 'o':
                    control_vlc(vlc_proc, 'volume_down')
                elif key == 'l':
                    control_vlc(vlc_proc, 'forward')
                elif key == 'k':
                    control_vlc(vlc_proc, 'backward')
                elif key == 'p':
                    control_vlc(vlc_proc, 'pause')
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

# -----------------------------
# Playback Handler
# -----------------------------
def handle_playback(vlc_proc, duration=None, title=None):
    def signal_handler(sig, frame):
        force_kill_vlc(vlc_proc)
        os._exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    screen_thread = None
    if duration is not None:
        screen_thread = threading.Thread(target=draw_screen, args=(vlc_proc, duration, title), daemon=True)
        screen_thread.start()

    try:
        vlc_proc.wait()
    except KeyboardInterrupt:
        force_kill_vlc(vlc_proc)
        os._exit(0)

# -----------------------------
# Main play function
# -----------------------------
def play(is_cli, *args):
    if not is_cli:
        query = " ".join(args)
        if query == ":r":
            query = random.choice(["https://www.youtube.com/watch?v=482tDopNzoc","https://www.youtube.com/watch?v=uaFzmZrKKKw","https://www.youtube.com/watch?v=7qqcZIHxyRI","https://www.youtube.com/watch?v=Cr4gKVsqh9o","https://www.youtube.com/watch?v=TnRZhLRv6eM"])
        url = get_audio_url(query)
        if not url:
            return 1
        vlc_proc = start_vlc(url)
        handle_playback(vlc_proc)

    if is_cli:
        print(Fore.CYAN + Style.BRIGHT + "♫ YTMCLI - YouTube Music CLI")
        print(Fore.MAGENTA + "----------------------------------")
        print(Fore.CYAN + "Press 'q' to quit, or Ctrl+C")
        query = input(Fore.YELLOW + Style.BRIGHT + "♫ Enter song > " + Style.RESET_ALL)
        if query == ":r":
            query = random.choice(["https://www.youtube.com/watch?v=482tDopNzoc","https://www.youtube.com/watch?v=uaFzmZrKKKw","https://www.youtube.com/watch?v=7qqcZIHxyRI","https://www.youtube.com/watch?v=Cr4gKVsqh9o","https://www.youtube.com/watch?v=TnRZhLRv6eM"])
        url, title, duration = get_audio_url(query, with_title=True, with_duration=True)
        if not url:
            return 1
        if title:
            print(Fore.GREEN + Style.BRIGHT + f"Title: {title}")
        vlc_proc = start_vlc(url)
        handle_playback(vlc_proc, duration, title)

# -----------------------------
# Entry
# -----------------------------
if __name__ == "__main__":
    is_cli = len(sys.argv) == 1
    play(is_cli, *sys.argv[1:])
