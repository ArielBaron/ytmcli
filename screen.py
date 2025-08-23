#!/usr/bin/env python3
"""
Screen display module - handles terminal UI, progress bars, and screen rendering
"""
import sys
import termios
import tty
import shutil
import time
from colorama import Fore, Style

# Import the visualizer module
try:
    from visualizer import AudioVisualizer
    VISUALIZER_AVAILABLE = True
except ImportError:
    VISUALIZER_AVAILABLE = False
    print("Warning: visualizer module not found")

# Import your existing modules
try:
    from vlc_client import get_status
    from controls import handle_input
except ImportError:
    # Fallback functions for testing
    def get_status():
        return {'time': 30, 'length': 180, 'state': 'playing', 'volume': 128}
    
    def handle_input(stdin, proc):
        import select
        if select.select([stdin], [], [], 0.1)[0]:
            char = stdin.read(1)
            if char.lower() == 'q':
                return "quit"
        return None

class MusicPlayerScreen:
    def __init__(self, width=None, height=None):
        # Terminal settings
        self.width = width or min(shutil.get_terminal_size().columns // 2, 100)
        self.height = height or min(shutil.get_terminal_size().lines // 2, 20)
        
        # Visualizer setup
        self.visualizer = None
        if VISUALIZER_AVAILABLE:
            self.visualizer = AudioVisualizer()
        
        # Terminal state
        self.fd = None
        self.old_settings = None
        
    def setup_terminal(self):
        """Setup terminal for non-blocking input"""
        self.fd = sys.stdin.fileno()
        self.old_settings = termios.tcgetattr(self.fd)
        tty.setcbreak(self.fd)
        
    def restore_terminal(self):
        """Restore original terminal settings"""
        if self.fd and self.old_settings:
            termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old_settings)
            
    def display_progress(self, duration, elapsed, percent):
        """Generate progress bar display"""
        bar_length = 30
        exact_pos = bar_length * percent / 100
        whole = int(exact_pos)
        frac = exact_pos - whole
        
        # Build progress bar with fractional characters
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
        
        # Format time displays
        elapsed_min, elapsed_sec = divmod(int(elapsed), 60)
        duration_min, duration_sec = divmod(int(duration), 60) if duration else (0, 0)
        remaining = max(0, duration - elapsed)
        rem_min, rem_sec = divmod(int(remaining), 60)
        
        return f'[{bar}] {elapsed_min:02d}:{elapsed_sec:02d} / {duration_min:02d}:{duration_sec:02d} [{rem_min:02d}:{rem_sec:02d} remaining]'

    def display_volume(self, volume):
        """Generate volume bar display"""
        vol_percent = int((volume / 256) * 100)
        bar_length = 20
        filled = int(bar_length * min(100, vol_percent) / 100)
        vol_bar = '█' * filled + '░' * (bar_length - filled)
        suffix = " (AMPLIFIED)" if vol_percent > 100 else ""
        return f'[{vol_bar}] {vol_percent}%{suffix} VOL'

    def display_playback_state(self, state):
        """Generate playback state display with colors"""
        if state == 'paused':
            return Fore.YELLOW + Style.BRIGHT + "⏸  PAUSED" + Style.RESET_ALL
        elif state == 'playing':
            return Fore.GREEN + Style.BRIGHT + "▶  PLAYING" + Style.RESET_ALL
        else:
            return Fore.RED + Style.BRIGHT + f"State: {state}" + Style.RESET_ALL

    def display_title(self, title):
        """Generate title display with formatting"""
        if title:
            return Fore.CYAN + Style.BRIGHT + title + Style.RESET_ALL
        return ""

    def display_controls(self):
        """Generate controls help text"""
        return "\n".join([
            "Press i or ↑ to increase volume",
            "Press o or ↓ to decrease volume", 
            "Press l or → to move forwards 5s",
            "Press k or ← to move backwards 5s",
            "Press p to pause/unpause",
            "Press q to quit",
            "Press r to remove current song from your history"
        ])

    def display_visualizer(self, state, num_bars=None, max_height=None):
        """Generate visualizer display"""
        if not self.visualizer:
            return "Audio visualizer not available"
            
        # Default sizing based on terminal
        if num_bars is None:
            num_bars = self.width // 4
        if max_height is None:
            max_height = self.height // 3
            
        if state == 'playing':
            header = Fore.MAGENTA + "Audio Visualizer:" + Style.RESET_ALL
            viz_content = self.visualizer.get_visualization(num_bars, max_height)
            return f"{header}\n{viz_content}"
        else:
            return Fore.MAGENTA + "Audio Visualizer: (paused)" + Style.RESET_ALL

    def clear_screen(self):
        """Clear screen and move cursor to top"""
        sys.stdout.write('\033[2J\033[H')

    def render_frame(self, status, title=None, show_visualizer=True):
        """Render a complete screen frame"""
        # Extract status info
        elapsed = status['time'] if status else 0
        duration = status['length'] if status else 0
        state = status['state'] if status else 'unknown'
        volume = status['volume'] if status else 128
        percent = min(100, (elapsed / duration * 100)) if duration > 0 else 0

        # Clear screen
        self.clear_screen()

        # Build screen content
        content = []
        
        # Playback state
        content.append(self.display_playback_state(state))
        
        # Title
        title_display = self.display_title(title)
        if title_display:
            content.append(title_display)

        # Progress and volume
        content.append("")  # Empty line
        content.append(self.display_progress(duration, elapsed, percent))
        content.append(self.display_volume(volume))

        # Visualizer
        if show_visualizer and self.visualizer:
            content.append("")  # Empty line
            content.append(self.display_visualizer(state))

        # Controls
        content.append("")  # Empty line
        content.append(self.display_controls())
        content.append("")  # Empty line

        # Print all content
        for line in content:
            print(line)

        sys.stdout.flush()

    def run_display_loop(self, vlc_proc, title=None, refresh_rate=0.05):
        """Main display loop"""
        self.setup_terminal()
        
        # Start visualizer if available
        if self.visualizer:
            self.visualizer.start_capture()

        try:
            while vlc_proc.poll() is None:
                # Get current status
                status = get_status()
                
                # Render frame
                self.render_frame(status, title, show_visualizer=True)

                # Handle input
                error = handle_input(sys.stdin, vlc_proc)
                if error:
                   return error; 

                # Control refresh rate
                time.sleep(refresh_rate)

        finally:
            self.restore_terminal()
            if self.visualizer:
                self.visualizer.stop_capture()

        return None

    def __enter__(self):
        """Context manager entry"""
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.restore_terminal()
        if self.visualizer:
            self.visualizer.stop_capture()


# Backward compatibility function
def draw_screen(vlc_proc, title=None, audio_file=None):
    """Original function signature for backward compatibility"""
    with MusicPlayerScreen() as screen:
        return screen.run_display_loop(vlc_proc, title)


# Test the screen if run directly
if __name__ == "__main__":
    class MockProcess:
        def __init__(self):
            self.start_time = time.time()
            
        def poll(self):
            # Auto-quit after 10 seconds for testing
            if time.time() - self.start_time > 10:
                return 1
            return None

    print("Testing music player screen...")
    print("Will auto-quit in 10 seconds or press 'q' to quit")
    
    try:
        with MusicPlayerScreen() as screen:
            screen.run_display_loop(MockProcess(), "Test Song - Test Artist")
    except KeyboardInterrupt:
        print("\nExiting...")