#!/usr/bin/env python3
"""
MPV-based audio client with full control via IPC
"""
import subprocess
import json
import socket
import time
import os
import threading
import tempfile

class MPVClient:
    def __init__(self):
        self.process = None
        self.socket_path = None
        self._socket_lock = threading.Lock()
        
    def start(self, url):
        """Start MPV with IPC interface"""
        if self.process and self.process.poll() is None:
            self.stop()
        
        # Create unique socket path
        fd, self.socket_path = tempfile.mkstemp(suffix='.sock', prefix='mpv_')
        os.close(fd)  # We don't need the file descriptor
        os.unlink(self.socket_path)  # Remove the temp file, we just want the path
        
        try:
            self.process = subprocess.Popen([
                "mpv",
                "--no-video",                           # Audio only
                "--input-ipc-server=" + self.socket_path,  # IPC socket
                "--idle",                               # Don't exit when playlist ends
                "--no-terminal",                        # Don't show terminal output
                "--msg-level=all=no",                   # Quiet output
                url
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Wait for socket to be created
            for _ in range(20):  # Wait up to 2 seconds
                if os.path.exists(self.socket_path):
                    time.sleep(0.1)  # Small delay to ensure socket is ready
                    return True
                time.sleep(0.1)
            
            print("Warning: MPV socket not created in time")
            return False
            
        except Exception as e:
            print(f"Error starting MPV: {e}")
            return False
    
    def _send_command(self, command, timeout=1.0):
        """Send IPC command to MPV"""
        with self._socket_lock:
            try:
                if not os.path.exists(self.socket_path):
                    return None
                
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                sock.settimeout(timeout)
                sock.connect(self.socket_path)
                
                command_json = json.dumps(command) + '\n'
                sock.sendall(command_json.encode())
                
                # Read response
                response = b''
                while True:
                    try:
                        chunk = sock.recv(1024)
                        if not chunk:
                            break
                        response += chunk
                        # Check if we have a complete JSON response
                        if b'\n' in response:
                            break
                    except socket.timeout:
                        break
                
                sock.close()
                
                if response:
                    # Parse first complete JSON line
                    response_str = response.decode().split('\n')[0]
                    if response_str:
                        return json.loads(response_str)
                
                return None
                
            except Exception as e:
                # Uncomment for debugging: print(f"IPC error: {e}")
                return None
    
    def get_property(self, prop):
        """Get MPV property"""
        response = self._send_command({"command": ["get_property", prop]})
        if response and response.get("error") == "success":
            return response.get("data")
        return None
    
    def set_property(self, prop, value):
        """Set MPV property"""
        response = self._send_command({"command": ["set_property", prop, value]})
        return response and response.get("error") == "success"
    
    def get_status(self):
        """Get playback status"""
        try:
            # Get all properties we need
            pause = self.get_property("pause")
            time_pos = self.get_property("time-pos")
            duration = self.get_property("duration")
            volume = self.get_property("volume")
            
            # Determine state
            state = "paused" if pause else "playing"
            if time_pos is None:
                state = "stopped"
                time_pos = 0
            
            return {
                'time': int(time_pos or 0),
                'length': int(duration or 0),
                'state': state,
                'volume': int((volume or 100) * 2.56)  # Convert to 0-256 range
            }
        except:
            return {
                'time': 0,
                'length': 0,
                'state': 'stopped',
                'volume': 256
            }
    
    def pause(self):
        """Toggle pause/play"""
        current_pause = self.get_property("pause")
        if current_pause is not None:
            return self.set_property("pause", not current_pause)
        return False
    
    def volume_up(self):
        """Increase volume by 10"""
        current_vol = self.get_property("volume")
        if current_vol is not None:
            new_vol = min(100, current_vol + 10)
            return self.set_property("volume", new_vol)
        return False
    
    def volume_down(self):
        """Decrease volume by 10"""
        current_vol = self.get_property("volume")
        if current_vol is not None:
            new_vol = max(0, current_vol - 10)
            return self.set_property("volume", new_vol)
        return False
    
    def seek(self, seconds):
        """Seek relative to current position"""
        response = self._send_command({"command": ["seek", seconds, "relative"]})
        return response and response.get("error") == "success"
    
    def stop(self):
        """Stop MPV"""
        if self.process and self.process.poll() is None:
            try:
                # Try graceful quit first
                self._send_command({"command": ["quit"]}, timeout=0.5)
                time.sleep(0.2)
                
                # Force terminate if still running
                if self.process.poll() is None:
                    self.process.terminate()
                    time.sleep(0.2)
                    
                    if self.process.poll() is None:
                        self.process.kill()
                        
            except:
                pass
        
        # Clean up socket
        if self.socket_path and os.path.exists(self.socket_path):
            try:
                os.unlink(self.socket_path)
            except:
                pass
        
        self.process = None
        self.socket_path = None
    
    def is_running(self):
        """Check if MPV is still running"""
        return self.process is not None and self.process.poll() is None
    
    def wait(self):
        """Wait for MPV to finish"""
        if self.process:
            return self.process.wait()
        return 0
    
    def poll(self):
        """Check if process has terminated"""
        if self.process:
            return self.process.poll()
        return 0


# Global MPV client instance
_player_client = MPVClient()

# Generic player interface functions
def start_player(url):
    """Start audio playback"""
    success = _player_client.start(url)
    if success:
        return _player_client
    return None

def get_status():
    """Get playback status"""
    return _player_client.get_status()

def control(action, value=None):
    """Control playback"""
    if action == 'pause' or action == 'play':
        return _player_client.pause()
    elif action == 'volume_up':
        return _player_client.volume_up()
    elif action == 'volume_down':
        return _player_client.volume_down()
    elif action == 'seek' and value:
        try:
            # Parse seek value like "+5" or "-5"
            seek_seconds = int(str(value).replace('+', ''))
            return _player_client.seek(seek_seconds)
        except:
            return False
    return False

def force_kill_player(proc):
    """Stop playback"""
    if hasattr(proc, 'stop'):
        proc.stop()
    else:
        _player_client.stop()

def wait_for_player_ready(max_wait=3):
    """Wait for player to be ready"""
    start_time = time.time()
    while time.time() - start_time < max_wait:
        if _player_client.socket_path and os.path.exists(_player_client.socket_path):
            # Test if we can communicate
            if _player_client.get_property("pause") is not None:
                return True
        time.sleep(0.1)
    return False

# Legacy VLC-compatible function names for backward compatibility
def start_vlc(url):
    """Legacy VLC-compatible function name"""
    return start_player(url)

def force_kill_vlc(proc):
    """Legacy VLC-compatible function name"""
    return force_kill_player(proc)

def wait_for_vlc_http(max_wait=3):
    """Legacy VLC-compatible function name"""
    return wait_for_player_ready(max_wait)