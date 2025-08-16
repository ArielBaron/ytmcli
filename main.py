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
        # Find bestaudio URL
        if 'formats' in info:
            for fmt in info['formats']:
                if fmt.get('acodec') != 'none' and fmt.get('vcodec') == 'none':
                    url = fmt.get('url')
                    break
        # Get title
        if with_title:
            title = info.get('title')
        # Get duration
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

def display_progress(vlc_proc, duration, elapsed, percent):
    """Display only the progress bar part"""
    # Progress bar setup
    bar_length = 30
    exact_position = bar_length * percent / 100
    
    # Split into whole and fractional parts
    whole_part = int(exact_position)
    fractional_part = exact_position - whole_part
    
    # Create smooth gradient effect
    bar = '█' * whole_part
    
    # Add fractional part with smooth transition
    if fractional_part > 0:
        if fractional_part <= 0.125:
            bar += ' '
        elif fractional_part <= 0.25:
            bar += '▏'
        elif fractional_part <= 0.375:
            bar += '▎'
        elif fractional_part <= 0.5:
            bar += '▍'
        elif fractional_part <= 0.625:
            bar += '▌'
        elif fractional_part <= 0.75:
            bar += '▋'
        elif fractional_part <= 0.875:
            bar += '▊'
        else:
            bar += '▉'
    
    # Fill remaining space
    remaining_space_char = ' '
    remaining_length = bar_length - len(bar)
    if remaining_length > 0:
        bar += remaining_space_char * remaining_length
    
    # Format time
    elapsed_min, elapsed_sec = divmod(int(elapsed), 60)
    duration_min, duration_sec = divmod(int(duration), 60) if duration else (0, 0)
    
    # Calculate remaining time
    remaining = max(0, duration - elapsed)
    remaining_min, remaining_sec = divmod(int(remaining), 60)
    
    # Print progress bar
    sys.stdout.write(
        f'[{bar}] {elapsed_min:02d}:{elapsed_sec:02d} / {duration_min:02d}:{duration_sec:02d} '
        f'[{percent:.1f}%] [{remaining_min:02d}:{remaining_sec:02d} remaining]\n'
    )

def display_controls():
    """Display control instructions at the bottom of the screen"""
    controls = [
        "Press ↑/i to increase volume",
        "Press ↓/o to decrease volume",
        "Press p to pause/unpause",
        "Press q to quit"
    ]
    return "\n".join(controls)

def draw_screen(vlc_proc, duration, title):
    """Draw the complete screen with title, progress bar and controls"""
    start_time = time.time()
    try:
        while vlc_proc.poll() is None:  # While VLC is still running
            elapsed = time.time() - start_time
            percent = min(100, (elapsed / duration * 100)) if duration else 0
            
            # Clear screen
            sys.stdout.write('\033[2J\033[H')  # Clear screen and move cursor to top
            
            # Display title if available
            if title:
                print(Fore.GREEN + Style.BRIGHT + f"Title: {title}")
                print()  # Add a blank line after title
            
            # Display progress bar
            display_progress(vlc_proc, duration, elapsed, percent)
            
            # Display controls
            print(display_controls())
            
            sys.stdout.flush()
            time.sleep(0.1)
    except KeyboardInterrupt:
        sys.stdout.write('\n')
        sys.stdout.flush()

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

def handle_playback(vlc_proc, duration=None, title=None):
    # Set up signal handlers for Ctrl+C
    def signal_handler(sig, frame):
        force_kill_vlc(vlc_proc)
        os._exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start quit monitor thread
    quit_thread = threading.Thread(target=monitor_quit, args=(vlc_proc,), daemon=True)
    quit_thread.start()
    
    # Start screen drawing thread if duration is available (CLI mode)
    screen_thread = None
    if duration is not None:
        screen_thread = threading.Thread(target=draw_screen, args=(vlc_proc, duration, title), daemon=True)
        screen_thread.start()
    
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
        url, title, duration = get_audio_url(query, with_title=True, with_duration=True)
        if not url:
            return 1
        if title:
            print(Fore.GREEN + Style.BRIGHT + f"Title: {title}")
        vlc_proc = start_vlc(url)
        handle_playback(vlc_proc, duration, title)

if __name__ == "__main__":
    is_cli = len(sys.argv) == 1
    play(is_cli, *sys.argv[1:])
