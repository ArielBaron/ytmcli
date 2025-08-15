#!/usr/bin/env python3
import subprocess
import sys
import threading

def play(*args):
    if not args:
        print("No query provided.")
        return 1

    query = " ".join(args)

    # Get direct audio URL from YouTube
    try:
        result = subprocess.run(
            ["yt-dlp", "-f", "bestaudio", "-g", f"ytsearch:{query}"],
            stdout=subprocess.PIPE,
            text=False,
            stderr=subprocess.DEVNULL
        )
        url = result.stdout.strip()
        if not url:
            print("No URL found.")
            return 1
    except Exception as e:
        print(f"Error getting URL: {e}")
        return 1

    # Start VLC in subprocess
    vlc_proc = subprocess.Popen(["cvlc", "--play-and-exit", "--quiet", url])

    # Function to monitor keyboard for 'q'
    def monitor_quit():
        while True:
            key = input()
            if key.strip().lower() == "q":
                vlc_proc.terminate()
                break

    # Start monitor in separate thread
    thread = threading.Thread(target=monitor_quit, daemon=True)
    thread.start()

    # Wait for VLC to finish
    vlc_proc.wait()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        play(*sys.argv[1:])
    else:
        query = input("Enter song: ")
        play(query)
