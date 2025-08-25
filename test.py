#!/usr/bin/env python3
"""
Quick test to see if mpv handles YouTube URLs better than VLC
"""
import subprocess
import time
import json
import socket
import os

def test_mpv():
    print("=== MPV Test ===")
    
    try:
        from get_audio_url import get_audio_url
        
        # Get YouTube URL
        result = get_audio_url("test song", with_title=True, with_duration=True)
        if not result or not result[0]:
            print("Could not get YouTube URL")
            return False
            
        url, title, duration = result
        print(f"Testing with: {title}")
        print(f"Duration: {duration}s")
        
        # Test basic mpv playback first
        print("\n1. Testing basic mpv playback...")
        proc = subprocess.Popen([
            "mpv", "--no-video", "--length=5", url
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        time.sleep(6)  # Let it play for 5 seconds
        return_code = proc.poll()
        
        if return_code == 0:
            print("✓ mpv can play YouTube URLs!")
        else:
            stdout, stderr = proc.communicate()
            print(f"✗ mpv failed with code {return_code}")
            if stderr:
                print(f"Error: {stderr.decode()[:200]}")
            return False
        
        # Test mpv with IPC interface
        print("\n2. Testing mpv IPC interface...")
        socket_path = "/tmp/mpv-socket"
        
        # Remove existing socket
        if os.path.exists(socket_path):
            os.unlink(socket_path)
            
        proc = subprocess.Popen([
            "mpv", "--no-video", "--input-ipc-server=" + socket_path,
            "--idle", url
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait for socket to be created
        for _ in range(10):
            if os.path.exists(socket_path):
                break
            time.sleep(0.5)
        
        if not os.path.exists(socket_path):
            print("✗ mpv IPC socket not created")
            proc.terminate()
            return False
        
        print("✓ mpv IPC socket created")
        
        # Test IPC commands
        def send_command(command):
            try:
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                sock.connect(socket_path)
                sock.sendall((json.dumps(command) + '\n').encode())
                response = sock.recv(4096).decode()
                sock.close()
                return json.loads(response) if response else None
            except Exception as e:
                print(f"IPC command error: {e}")
                return None
        
        time.sleep(1)  # Let mpv initialize
        
        # Test getting properties
        print("\n3. Testing IPC commands...")
        
        # Get playback status
        status = send_command({"command": ["get_property", "pause"]})
        if status:
            print(f"✓ Get pause status: {status}")
        
        # Get time position
        time_pos = send_command({"command": ["get_property", "time-pos"]})
        if time_pos:
            print(f"✓ Get time position: {time_pos}")
        
        # Get volume
        volume = send_command({"command": ["get_property", "volume"]})
        if volume:
            print(f"✓ Get volume: {volume}")
        
        # Test volume control
        vol_result = send_command({"command": ["set_property", "volume", 50]})
        if vol_result is not None:
            print("✓ Volume control works")
        
        # Test seeking
        seek_result = send_command({"command": ["seek", 10, "relative"]})
        if seek_result is not None:
            print("✓ Seeking works")
        
        # Test pause/play
        pause_result = send_command({"command": ["set_property", "pause", True]})
        if pause_result is not None:
            print("✓ Pause control works")
        
        proc.terminate()
        proc.wait()
        
        # Clean up socket
        if os.path.exists(socket_path):
            os.unlink(socket_path)
        
        print("\n✓ mpv with IPC looks promising!")
        return True
        
    except ImportError:
        print("Could not import get_audio_url")
        return False
    except FileNotFoundError:
        print("✗ mpv not installed (try: sudo apt install mpv)")
        return False
    except Exception as e:
        print(f"Test error: {e}")
        return False

if __name__ == "__main__":
    test_mpv()