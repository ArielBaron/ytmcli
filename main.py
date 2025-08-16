#!/usr/bin/env python3
import subprocess
import sys
import threading

def play(*args):
    if not args:
        print("No query provided.")
        return 1

    query = " ".join(args)

    # Get direct audio URL from yt-dlp
    try:
        result = subprocess.run(
            ["yt-dlp", "-f", "bestaudio", "-g", f"ytsearch:{query}"],
            capture_output=True,
            text=True
        )
        url = result.stdout.strip()
        if not url:
            print("No URL found.")
            return 1
    except Exception as e:
        print(f"Error getting URL: {e}")
        return 1

    # Start VLC in subprocess (suppress output completely)
    vlc_proc = subprocess.Popen(
        ["cvlc", "--play-and-exit", "--quiet", url],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    # Function to monitor keyboard for 'q'
    def monitor_quit():
        while True:
            key = input()
            if key.strip().lower() == "q":
                vlc_proc.terminate()
                break

    threading.Thread(target=monitor_quit, daemon=True).start()
    vlc_proc.wait()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        play(*sys.argv[1:])
    else:
        query = input("Enter song: ")
        play(query)
