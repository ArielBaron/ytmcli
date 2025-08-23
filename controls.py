import select
from history import YTMCLIHistory
from vlc_client import control, force_kill_vlc

def handle_input(system_input, vlc_proc):
    """
    Handle a single keypress from the user.

    Parameters:
    - system_input: file-like object (e.g., sys.stdin) to read input from.
    - vlc_proc: VLC process instance to control playback.

    Behavior:
    - Maps specific keypresses (arrows, i/o/l/k/p/r/s/q) to VLC actions or history updates.
    - Non-blocking: returns immediately if no input is available.
    - Returns:
        - "quit" if user pressed q
        - "stop" if user pressed s
        - None otherwise
    """
    history = YTMCLIHistory()

    if select.select([system_input], [], [], 0)[0]:
        key = system_input.read(1).lower()

        # Arrow keys
        if key == '\x1b':
            key += system_input.read(2)
            if key == '\x1b[A': control('volume_up')
            elif key == '\x1b[B': control('volume_down')
            elif key == '\x1b[C': control('seek', '+5')
            elif key == '\x1b[D': control('seek', '-5')

        # Quit
        elif key == 'q':
            force_kill_vlc(vlc_proc)
            return "quit"

        # Stop (just stop playback, return to CLI)
        elif key == 's':
            force_kill_vlc(vlc_proc)
            return "stop"

        # Volume
        elif key == 'i': control('volume_up')
        elif key == 'o': control('volume_down')

        # Seek
        elif key == 'l': control('seek', '+5')
        elif key == 'k': control('seek', '-5')

        # Pause
        elif key == 'p': control('pause')

        # Remove last from history
        elif key == 'r': history.delete_last()

    return None
