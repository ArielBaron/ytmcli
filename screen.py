#!/usr/bin/env python3
import sys
import termios
import tty
import select
import shutil
import subprocess
from colorama import Fore, Back, Style
from vlc_client import control, get_status, force_kill_vlc
from history import YTMCLIHistory
# Terminal settings
WIDTH = min(shutil.get_terminal_size().columns // 2, 100)
HEIGHT = min(shutil.get_terminal_size().lines // 2, 20)

def display_progress(duration, elapsed, percent):
    bar_length = 30
    exact_pos = bar_length * percent / 100
    whole = int(exact_pos)
    frac = exact_pos - whole
    bar = '█' * whole
    if frac > 0:
        if frac <= 0.125: bar += ' '
        elif frac <= 0.25:  bar += '▏'
        elif frac <= 0.375: bar += '▎'
        elif frac <= 0.5:   bar += '▍'
        elif frac <= 0.625: bar += '▌'
        elif frac <= 0.75:  bar += '▋'
        elif frac <= 0.875: bar += '▊'
        else:               bar += '▉'
    bar += ' ' * (bar_length - len(bar))
    elapsed_min, elapsed_sec = divmod(int(elapsed), 60)
    duration_min, duration_sec = divmod(int(duration), 60) if duration else (0, 0)
    remaining = max(0, duration - elapsed)
    rem_min, rem_sec = divmod(int(remaining), 60)
    return f'[{bar}] {elapsed_min:02d}:{elapsed_sec:02d} / {duration_min:02d}:{duration_sec:02d} [{rem_min:02d}:{rem_sec:02d} remaining]'

def display_volume(volume):
    vol_percent = int((volume / 256) * 100)
    bar_length = 20
    filled = int(bar_length * min(100, vol_percent) / 100)
    vol_bar = '█' * filled + '░' * (bar_length - filled)
    suffix = " (AMPLIFIED)" if vol_percent > 100 else ""
    return f'[{vol_bar}] {vol_percent}%{suffix} VOL'

def display_controls():
    return "\n".join([
        "Press i or ↑ to increase volume",
        "Press o or ↓ to decrease volume",
        "Press l or → to move forwards 5s",
        "Press k or ← to move backwards 5s",
        "Press p to pause/unpause",
        "Press q to quit",
        "press r to remove current song from you history"
    ])

def draw_screen(vlc_proc, title=None):
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    tty.setcbreak(fd)


    try:
        while vlc_proc.poll() is None:
            status = get_status()
            elapsed = status['time'] if status else 0
            duration = status['length'] if status else 0
            state = status['state'] if status else 'unknown'
            percent = min(100, (elapsed / duration * 100)) if duration > 0 else 0

            # Clear screen
            sys.stdout.write('\033[2J\033[H')

            # Playback state
            if state == 'paused':
                print(Fore.YELLOW + Style.BRIGHT + "⏸  PAUSED")
            elif state == 'playing':
                print(Fore.GREEN + Style.BRIGHT + "▶  PLAYING")
            else:
                print(Fore.RED + Style.BRIGHT + f"State: {state}")

            if title:
                print(Fore.GREEN + Style.BRIGHT + title)

            print()
            print(display_progress(duration, elapsed, percent))
            if status:
                print(display_volume(status['volume']))
            print()
            print(display_controls())
            print()


            sys.stdout.flush()

            # Handle input
            history = YTMCLIHistory()
            if select.select([sys.stdin], [], [], 0)[0]:
                key = sys.stdin.read(1).lower()
                if key == '\x1b':
                    key += sys.stdin.read(2)
                    if key == '\x1b[A': control('volume_up')
                    elif key == '\x1b[B': control('volume_down')
                    elif key == '\x1b[C': control('seek', '+5')
                    elif key == '\x1b[D': control('seek', '-5')
                elif key == 'q':
                    force_kill_vlc(vlc_proc)
                    return 'user pressed q'
                elif key == 'i': control('volume_up')
                elif key == 'o': control('volume_down')
                elif key == 'l': control('seek', '+5')
                elif key == 'k': control('seek', '-5')
                elif key == 'p': control('pause')
                elif key == 'r': history.delete_last()
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
