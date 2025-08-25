#!/usr/bin/env python3
import sys
import threading
import random
import time
from colorama import init, Fore, Style
from get_audio_url import get_audio_url
from mpv_client import start_player, force_kill_player, get_status, wait_for_player_ready, control
from screen import draw_screen
from history import YTMCLIHistory

init(autoreset=True)

def handle_playback(player_proc, title=None):
    """
    Starts the visualizer thread and waits for player playback.
    Returns True if playback was stopped by user (q or Ctrl+C), False otherwise.
    """
    stopped_by_user = False
    exit_reason = ""
    
    def screen_runner():
        nonlocal exit_reason
        nonlocal stopped_by_user
        try:
            error = draw_screen(player_proc, title)
            if error:
                exit_reason = error
                stopped_by_user = True
        except KeyboardInterrupt:
            exit_reason = "exit"
            stopped_by_user = True
    
    # Give player a moment to initialize and wait for interface
    time.sleep(0.5)
    
    # Wait for interface to be ready
    if wait_for_player_ready(max_wait=3):
        initial_status = get_status()
        print(Fore.GREEN + f"Player interface ready. Status: {initial_status}")
        
        # If player is stopped, try to start playback
        if initial_status and initial_status.get('state') == 'stopped':
            print(Fore.YELLOW + "Player is stopped, sending play command...")
            control('play')
            time.sleep(0.5)  # Give it a moment to start
            
            # Check status again
            updated_status = get_status()
            if updated_status:
                print(Fore.CYAN + f"Updated status: {updated_status}")
    else:
        print(Fore.RED + "Warning: Could not connect to player interface within 3 seconds")
    
    screen_thread = threading.Thread(target=screen_runner, daemon=True)
    screen_thread.start()
    
    try:
        # Monitor player process
        start_time = time.time()
        while player_proc.poll() is None:
            time.sleep(0.1)
            
            # Check if player has been running for a reasonable amount of time
            if time.time() - start_time > 1:
                status = get_status()
                if status and status.get('state') == 'stopped':
                    print(Fore.YELLOW + "Player reports stopped state")
                    break
                    
        # Player process has ended
        return_code = player_proc.poll()
        print(Fore.CYAN + f"Player process ended with return code: {return_code}")
        
        # If we reach here and weren't stopped by user, the song finished naturally
        if not stopped_by_user:
            print(Fore.GREEN + "Song finished playing")
            
    except KeyboardInterrupt:
        print(Fore.YELLOW + "Interrupted by user")
        force_kill_player(player_proc)
        stopped_by_user = True
        exit_reason = "interrupt"
    finally:
        # Wait for screen thread to finish
        if screen_thread.is_alive():
            screen_thread.join(timeout=1)
    
    return stopped_by_user, exit_reason

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
        
        try:
            print(Fore.CYAN + f"Searching for: {query}")
            result = get_audio_url(query, with_title=True, with_duration=True)
            if result and result[0]:
                url, title, duration = result
                print(Fore.GREEN + f"Found: {title}")
                print(Fore.BLUE + f"Duration: {duration}s")
                print(Fore.BLUE + f"URL: {url[:100]}...")
                history.add(query)
                player_proc = start_player(url)
                handle_playback(player_proc, title)
            else:
                print(Fore.RED + "No audio URL found")
        except Exception as e:
            print(Fore.RED + f"Error: {e}")
            import traceback
            traceback.print_exc()
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
        
        if not query.strip():
            continue
            
        query = resolve_special_query(query, history)
        if not query:
            continue  # special command handled (don't use command as actual query)
        
        try:
            print(Fore.CYAN + f"Searching for: {query}")
            result = get_audio_url(query, with_title=True, with_duration=True)
            
            if result and result[0]:  # Check if we got a valid result
                url, title, duration = result
                print(Fore.GREEN + f"Found: {title}")
                if duration:
                    print(Fore.BLUE + f"Duration: {duration}s")
                
                # Test if URL is accessible (quick check)
                try:
                    import requests
                    response = requests.head(url, timeout=3)
                    if response.status_code not in [200, 206]:  # 206 is partial content, common for media
                        print(Fore.RED + f"URL may be invalid (status: {response.status_code})")
                        continue
                    print(Fore.GREEN + "URL is accessible")
                except Exception as e:
                    print(Fore.YELLOW + f"Could not verify URL accessibility: {e}")
                    # Continue anyway, might still work
                
                print(Fore.BLUE + f"URL: {url[:100]}...")
                
                history.add(query)
                player_proc = start_player(url)
                
                # Wait for player interface to be ready
                if not wait_for_player_ready(max_wait=3):
                    print(Fore.RED + "Could not establish connection to player")
                    force_kill_player(player_proc)
                    continue
                
                # Send play command to start playback
                print(Fore.CYAN + "Starting playback...")
                control('play')
                time.sleep(0.5)  # Give player time to start playing
                
                stopped, exit_reason = handle_playback(player_proc, title)
                
                if stopped:
                    if exit_reason == 'quit':
                        print(Fore.GREEN + "Goodbye!")
                        break
                    elif exit_reason == "stop":
                        print(Fore.YELLOW + "Playback stopped")
                        continue
                    elif exit_reason == "interrupt":
                        print(Fore.YELLOW + "Playback interrupted")
                        continue
                else:
                    print(Fore.GREEN + "Song completed")
            else:
                print(Fore.RED + "Could not find audio for that query. Try again.")
                
        except Exception as e:
            print(Fore.RED + f"Error getting audio: {e}")
            import traceback
            traceback.print_exc()
            continue

if __name__ == "__main__":
    is_cli = (len(sys.argv) == 1)
    play(is_cli, *sys.argv[1:])