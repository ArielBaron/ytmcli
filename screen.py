#!/usr/bin/env python3
import sys
import termios
import tty
import select
from colorama import Fore, Style
from vlc_client import control, get_status, force_kill_vlc

def display_progress(duration, elapsed, percent):
    bar_length = 30
    exact_pos = bar_length * percent / 100
    whole = int(exact_pos)
    frac = exact_pos - whole
    bar = '█' * whole
    if frac > 0:
        if frac <= 0.125: bar += ' '
        elif frac <= 0.25: bar += '▏'
        elif frac <= 0.375: bar += '▎'
        elif frac <= 0.5: bar += '▍'
        elif frac <= 0.625: bar += '▌'
        elif frac <= 0.75: bar += '▋'
        elif frac <= 0.875: bar += '▊'
        else: bar += '▉'
    bar += ' ' * (bar_length - len(bar))
    elapsed_min, elapsed_sec = divmod(int(elapsed), 60)
    duration_min, duration_sec = divmod(int(duration), 60) if duration else (0,0)
    remaining = max(0, duration - elapsed)
    rem_min, rem_sec = divmod(int(remaining), 60)
    print(f'[{bar}] {elapsed_min:02d}:{elapsed_sec:02d} / {duration_min:02d}:{duration_sec:02d}'
          f' [{rem_min:02d}:{rem_sec:02d} remaining]')

def display_volume(volume):
    vol_percent = int((volume / 256) * 100)
    bar_length = 20
    filled = int(bar_length * min(100, vol_percent) / 100)
    vol_bar = '█' * filled + '░' * (bar_length - filled)
    vol_icon = "🔇" if vol_percent == 0 else "🔈" if vol_percent < 30 else "🔉" if vol_percent < 70 else "🔊"
    suffix = " (AMPLIFIED)" if vol_percent > 100 else ""
    print(f'{vol_icon} Volume: [{vol_bar}] {vol_percent}%{suffix}')

def display_controls():
    return "\n".join([
        "Press i or ↑ to increase volume",
        "Press o or ↓ to decrease volume",
        "Press l or → to move forwards 5s",
        "Press k or ← to move backwards 5s",
        "Press p to pause/unpause",
        "Press q to quit"
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

            if select.select([sys.stdin], [], [], 0)[0]:
                key = sys.stdin.read(1).lower()
                if key == '\x1b':
                    key += sys.stdin.read(2)
                    if key == '\x1b[A': control('volume_up')
                    elif key == '\x1b[B': control('volume_down')
                    elif key == '\x1b[C': control('seek', '+5')
                    elif key == '\x1b[D': control('seek', '-5')
                elif key == 'q':
                    force_kill_vlc(vlc_proc); exit(0)
                elif key == 'i': control('volume_up')
                elif key == 'o': control('volume_down')
                elif key == 'l': control('seek', '+5')
                elif key == 'k': control('seek', '-5')
                elif key == 'p': control('pause')
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
