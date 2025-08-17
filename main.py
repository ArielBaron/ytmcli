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
import requests
from urllib.parse import quote

init(autoreset=True)

# -----------------------------
# YouTube URL fetching
# -----------------------------
def get_audio_url(query, with_title=False, with_duration=False):
    try:
        result = subprocess.run(
            ["yt-dlp", "--extractor-args", "youtube:player_client=android_music", "-f", "bestaudio", "-j", f"ytsearch:{query}"],
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
# VLC Control with HTTP Interface
# -----------------------------
def start_vlc(url):
    """Start VLC with HTTP interface"""
    return subprocess.Popen(
        ["cvlc", "--play-and-exit", "--quiet", 
         "--extraintf", "http", "--http-password", "vlc", "--http-port", "8080",
         url],
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True
    )

def force_kill_vlc(vlc_proc):
    if vlc_proc.poll() is None:
        vlc_proc.terminate()
        time.sleep(0.1)
        if vlc_proc.poll() is None:
            vlc_proc.kill()

def get_vlc_status():
    """Get current VLC status via HTTP interface"""
    try:
        response = requests.get("http://:vlc@localhost:8080/requests/status.json", timeout=1)
        if response.status_code == 200:
            data = response.json()
            return {
                'time': data.get('time', 0),
                'length': data.get('length', 0),
                'state': data.get('state', 'stopped'),
                'volume': data.get('volume', 256)
            }
    except:
        pass
    return None

def control_vlc_http(action, value=None):
    """Send HTTP commands to VLC"""
    try:
        base_url = "http://:vlc@localhost:8080/requests/status.json"
        
        if action == 'pause':
            requests.get(f"{base_url}?command=pl_pause", timeout=1)
        elif action == 'volume_up':
            requests.get(f"{base_url}?command=volume&val=+10", timeout=1)
        elif action == 'volume_down':
            requests.get(f"{base_url}?command=volume&val=-10", timeout=1)
        elif action == 'seek':
            if value:
                requests.get(f"{base_url}?command=seek&val={value}", timeout=1)
    except:
        pass

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
          f' [{remaining_min:02d}:{remaining_sec:02d} remaining]')

def display_volume(volume):
    vol_percent = int((volume / 256) * 100)
    bar_length = 20
    
    bar_percent = min(100, vol_percent)
    filled = int(bar_length * bar_percent / 100)
    
    vol_bar = '█' * filled + '░' * (bar_length - filled)
    
    if vol_percent == 0:
        vol_icon = "🔇"
    elif vol_percent < 30:
        vol_icon = "🔈"
    elif vol_percent < 70:
        vol_icon = "🔉"
    else:
        vol_icon = "🔊"
    
    if vol_percent > 100:
        print(f'{vol_icon} Volume: [{vol_bar}] {vol_percent}% (AMPLIFIED)')
    else:
        print(f'{vol_icon} Volume: [{vol_bar}] {vol_percent}%')

def display_controls():
    controls = [
        "Press i or ↑ to increase volume",
        "Press o or ↓ to decrease volume", 
        "Press l or → to move forwards 5s",
        "Press k or ← to move backwards 5s",
        "Press p to pause/unpause",
        "Press q to quit"
    ]
    return "\n".join(controls)

def draw_screen(vlc_proc, title):
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    tty.setcbreak(fd)

    try:
        while vlc_proc.poll() is None:
            status = get_vlc_status()
            
            if status:
                elapsed = status['time']
                duration = status['length'] 
                state = status['state']
                
                if duration > 0:
                    percent = min(100, (elapsed / duration * 100))
                else:
                    percent = 0
                    duration = 0
            else:
                elapsed = 0
                duration = 0
                percent = 0
                state = 'unknown'

            sys.stdout.write('\033[2J\033[H')
            if state == 'paused':
                print(Fore.YELLOW + Style.BRIGHT + "⏸  PAUSED")
            elif state == 'playing':
                print(Fore.GREEN + Style.BRIGHT + "▶  PLAYING")
            else:
                print(Fore.RED + Style.BRIGHT + f"State: {state}")
            
            if title:
                print(Fore.GREEN + Style.BRIGHT + title)
            
            print()
            display_progress(duration, elapsed, percent)
            if status:
                display_volume(status['volume'])
            print()
            print(display_controls())
            sys.stdout.flush()
            
            time.sleep(0.5)

            if select.select([sys.stdin], [], [], 0)[0]:
                key = sys.stdin.read(1)
                
                if key == '\x1b':
                    key += sys.stdin.read(2)
                    if key == '\x1b[A':
                        control_vlc_http('volume_up')
                    elif key == '\x1b[B':
                        control_vlc_http('volume_down')
                    elif key == '\x1b[C':
                        control_vlc_http('seek', '+5')
                    elif key == '\x1b[D':
                        control_vlc_http('seek', '-5')
                else:
                    key = key.lower()
                    if key == 'q':
                        force_kill_vlc(vlc_proc)
                        os._exit(0)
                    elif key == 'i':
                        control_vlc_http('volume_up')
                    elif key == 'o':
                        control_vlc_http('volume_down')
                    elif key == 'l':
                        control_vlc_http('seek', '+5')
                    elif key == 'k':
                        control_vlc_http('seek', '-5')
                    elif key == 'p':
                        control_vlc_http('pause')
                    
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

# -----------------------------
# Playback Handler
# -----------------------------
def handle_playback(vlc_proc, title=None):
    def signal_handler(sig, frame):
        force_kill_vlc(vlc_proc)
        os._exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    time.sleep(2)
    
    screen_thread = threading.Thread(target=draw_screen, args=(vlc_proc, title), daemon=True)
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
            query = random.choice([
                "https://www.youtube.com/watch?v=482tDopNzoc",
                "https://www.youtube.com/watch?v=uaFzmZrKKKw",
                "https://www.youtube.com/watch?v=7qqcZIHxyRI",
                "https://www.youtube.com/watch?v=Cr4gKVsqh9o",
                "https://www.youtube.com/watch?v=TnRZhLRv6eM"
            ])
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
            query = random.choice([
                "https://www.youtube.com/watch?v=482tDopNzoc",
                "https://www.youtube.com/watch?v=uaFzmZrKKKw",
                "https://www.youtube.com/watch?v=7qqcZIHxyRI",
                "https://www.youtube.com/watch?v=Cr4gKVsqh9o",
                "https://www.youtube.com/watch?v=TnRZhLRv6eM"
            ])
        url, title, duration = get_audio_url(query, with_title=True, with_duration=True)
        if not url:
            return 1
        vlc_proc = start_vlc(url)
        handle_playback(vlc_proc, title)

# -----------------------------
# Entry
# -----------------------------
if __name__ == "__main__":
    is_cli = len(sys.argv) == 1
    play(is_cli, *sys.argv[1:])
