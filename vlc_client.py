#!/usr/bin/env python3
import subprocess
import requests
import time
#sadssdasda
def start_vlc(url):
    """Start VLC with HTTP interface"""
    return subprocess.Popen(
        ["cvlc", "--play-and-exit", "--quiet", 
         "--extraintf", "http", "--http-password", "vlc", "--http-port", "8080",
         url],
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True
    )

def force_kill_vlc(vlc_proc):
    if vlc_proc.poll() is None:
        vlc_proc.terminate()
        time.sleep(0.1)
        if vlc_proc.poll() is None:
            vlc_proc.kill()

def get_status():
    """Return dict with time, length, state, volume"""
    try:
        resp = requests.get("http://:vlc@localhost:8080/requests/status.json", timeout=1)
        if resp.status_code == 200:
            data = resp.json()
            return {
                'time': data.get('time', 0),
                'length': data.get('length', 0),
                'state': data.get('state', 'stopped'),
                'volume': data.get('volume', 256)
            }
    except:
        pass
    return None

def control(action, value=None):
    """Send commands to VLC"""
    try:
        base_url = "http://:vlc@localhost:8080/requests/status.json"
        if action == 'pause':
            requests.get(f"{base_url}?command=pl_pause", timeout=1)
        elif action == 'volume_up':
            requests.get(f"{base_url}?command=volume&val=+10", timeout=1)
        elif action == 'volume_down':
            requests.get(f"{base_url}?command=volume&val=-10", timeout=1)
        elif action == 'seek' and value:
            requests.get(f"{base_url}?command=seek&val={value}", timeout=1)
    except:
        pass
