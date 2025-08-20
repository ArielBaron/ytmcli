#!/usr/bin/env python3
"""
Audio visualizer module - handles real-time audio capture and FFT visualization
"""
import numpy as np
import threading
import time
import queue
from colorama import Fore, Style

try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False

class AudioVisualizer:
    def __init__(self, sample_rate=44100, chunk_size=1024, max_queue_size=10):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.audio_data_queue = queue.Queue(maxsize=max_queue_size)
        self.capture_thread = None
        self.stop_event = threading.Event()
        self.is_running = False
        
    def start_capture(self):
        """Start audio capture in a separate thread"""
        if not PYAUDIO_AVAILABLE:
            return False
            
        if self.is_running:
            return True
            
        self.stop_event.clear()
        self.capture_thread = threading.Thread(target=self._capture_audio, daemon=True)
        self.capture_thread.start()
        self.is_running = True
        return True
        
    def stop_capture(self):
        """Stop audio capture thread"""
        self.stop_event.set()
        self.is_running = False
        if self.capture_thread and self.capture_thread.is_alive():
            self.capture_thread.join(timeout=1)
            
    def _capture_audio(self):
        """Audio capture thread function"""
        try:
            p = pyaudio.PyAudio()
            
            stream = p.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size
            )
            
            while not self.stop_event.is_set():
                try:
                    data = stream.read(self.chunk_size, exception_on_overflow=False)
                    audio_array = np.frombuffer(data, dtype=np.int16).astype(np.float32)
                    
                    # Non-blocking queue put
                    try:
                        self.audio_data_queue.put_nowait(audio_array)
                    except queue.Full:
                        # Remove old data and add new
                        try:
                            self.audio_data_queue.get_nowait()
                            self.audio_data_queue.put_nowait(audio_array)
                        except queue.Empty:
                            pass
                            
                except Exception as e:
                    print(f"Audio capture error: {e}")
                    break
                    
            stream.stop_stream()
            stream.close()
            p.terminate()
            
        except Exception as e:
            print(f"Audio thread initialization error: {e}")
            
    def get_latest_audio_data(self):
        """Get the most recent audio data for visualization"""
        try:
            return self.audio_data_queue.get_nowait()
        except queue.Empty:
            return None
            
    def generate_fft_bars(self, audio_data, num_bars=20, max_height=8):
        """Generate FFT-based visualization bars from audio data"""
        if audio_data is None or len(audio_data) == 0:
            return [0] * num_bars
            
        try:
            # Apply window function
            windowed = audio_data * np.hanning(len(audio_data))
            
            # FFT
            fft_vals = np.abs(np.fft.rfft(windowed))
            
            # Logarithmically spaced frequency bins
            if len(fft_vals) > num_bars:
                indices = np.logspace(0, np.log10(len(fft_vals)-1), num_bars).astype(int)
                fft_vals = fft_vals[indices]
            else:
                fft_vals = fft_vals[:num_bars]
                
            # Apply log scaling for better dynamics
            fft_vals = np.log1p(fft_vals)
            
            # Normalize to max_height
            if np.max(fft_vals) > 0:
                fft_vals = (fft_vals / np.max(fft_vals)) * max_height
                
            return [int(val) for val in fft_vals]
            
        except Exception as e:
            print(f"FFT error: {e}")
            return [0] * num_bars
            
    def render_bars_ascii(self, bars, max_height=8, use_colors=True):
        """Render visualization bars as ASCII art"""
        lines = []
        
        for row in reversed(range(max_height)):
            line = ''
            for bar_height in bars:
                if bar_height > row:
                    if use_colors:
                        # Color coding based on frequency range
                        if row < max_height // 3:
                            line += Fore.RED + '█' + Style.RESET_ALL + ' '
                        elif row < 2 * max_height // 3:
                            line += Fore.YELLOW + '█' + Style.RESET_ALL + ' '
                        else:
                            line += Fore.GREEN + '█' + Style.RESET_ALL + ' '
                    else:
                        line += '█ '
                else:
                    line += '  '
            lines.append(line)
            
        return '\n'.join(lines)
        
    def generate_fake_bars(self, num_bars=20, max_height=8):
        """Generate fake animated bars for testing/fallback"""
        import random
        return [random.randint(0, max_height) for _ in range(num_bars)]
        
    def get_visualization(self, num_bars=20, max_height=8, use_colors=True, fallback_mode=False):
        """Get complete visualization string"""
        if fallback_mode or not PYAUDIO_AVAILABLE:
            if not PYAUDIO_AVAILABLE:
                return "Audio visualizer disabled (pyaudio not available)\nInstall with: pip install pyaudio"
            bars = self.generate_fake_bars(num_bars, max_height)
        else:
            audio_data = self.get_latest_audio_data()
            if audio_data is not None:
                bars = self.generate_fft_bars(audio_data, num_bars, max_height)
            else:
                bars = self.generate_fake_bars(num_bars, max_height)
                
        return self.render_bars_ascii(bars, max_height, use_colors)
        
    def is_audio_available(self):
        """Check if audio capture is available"""
        return PYAUDIO_AVAILABLE
        
    def __enter__(self):
        """Context manager entry"""
        self.start_capture()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.stop_capture()


# Convenience functions for backward compatibility
_global_visualizer = None

def start_audio_capture():
    """Start global audio capture"""
    global _global_visualizer
    if _global_visualizer is None:
        _global_visualizer = AudioVisualizer()
    return _global_visualizer.start_capture()

def stop_audio_capture():
    """Stop global audio capture"""
    global _global_visualizer
    if _global_visualizer:
        _global_visualizer.stop_capture()

def draw_visualizer(num_bars=20, max_height=8):
    """Draw visualizer using global instance (for backward compatibility)"""
    global _global_visualizer
    if _global_visualizer is None:
        _global_visualizer = AudioVisualizer()
        _global_visualizer.start_capture()
    
    return _global_visualizer.get_visualization(num_bars, max_height)


# Test the visualizer if run directly
if __name__ == "__main__":
    print("Testing audio visualizer...")
    print("Press Ctrl+C to quit")
    
    with AudioVisualizer() as viz:
        try:
            while True:
                print('\033[2J\033[H')  # Clear screen
                print("Real-time Audio Visualizer Test")
                print("=" * 40)
                print(viz.get_visualization(num_bars=30, max_height=10))
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\nExiting...")