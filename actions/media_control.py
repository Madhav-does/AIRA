"""
ARIA Media Control
Controls Spotify, YouTube, and system media playback.
- Sends media key events (Play/Pause, Next, Previous)
- Spotify: search & play via web URL
- YouTube: search and play in browser
"""

import subprocess
import time
import webbrowser
import urllib.parse

try:
    import ctypes
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False


# Virtual key codes for media keys
VK_MEDIA_PLAY_PAUSE = 0xB3
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_STOP       = 0xB2
KEYEVENTF_KEYUP     = 0x0002


def _send_media_key(vk_code: int):
    """Send a virtual media key press (works system-wide)."""
    if WIN32_AVAILABLE:
        ctypes.windll.user32.keybd_event(vk_code, 0, 0, 0)
        time.sleep(0.05)
        ctypes.windll.user32.keybd_event(vk_code, 0, KEYEVENTF_KEYUP, 0)
        return True
    return False


def play_pause() -> bool:
    """Toggle play/pause on whatever is currently playing."""
    print("[MediaControl] Play/Pause")
    return _send_media_key(VK_MEDIA_PLAY_PAUSE)


def next_track() -> bool:
    """Skip to the next track."""
    print("[MediaControl] Next Track")
    return _send_media_key(VK_MEDIA_NEXT_TRACK)


def prev_track() -> bool:
    """Go to the previous track."""
    print("[MediaControl] Previous Track")
    return _send_media_key(VK_MEDIA_PREV_TRACK)


def stop_media() -> bool:
    """Stop media playback."""
    print("[MediaControl] Stop")
    return _send_media_key(VK_MEDIA_STOP)


def play_on_spotify(query: str) -> str:
    """
    Search for and play a song/artist/playlist on Spotify.
    Opens Spotify web search — if Spotify app is open it will play there.
    """
    encoded = urllib.parse.quote_plus(query)
    # Use the Spotify URI scheme first (plays in app), fall back to web
    uri = f"spotify:search:{encoded}"
    web = f"https://open.spotify.com/search/{encoded}"

    try:
        import subprocess, os
        # Try to open via Spotify URI (opens Spotify app directly)
        spotify_exe = os.path.expandvars(r'%LOCALAPPDATA%\Microsoft\WindowsApps\Spotify.exe')
        if os.path.exists(spotify_exe):
            subprocess.Popen([spotify_exe, '--uri', uri],
                             creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)
        else:
            webbrowser.open(web)
        print(f"[MediaControl] Spotify search: {query}")
        return web
    except Exception:
        webbrowser.open(web)
        return web


def play_on_youtube(query: str) -> str:
    """Search for and open a video on YouTube in the browser."""
    encoded = urllib.parse.quote_plus(query)
    url = f"https://www.youtube.com/results?search_query={encoded}"
    webbrowser.open(url)
    print(f"[MediaControl] YouTube search: {query}")
    return url
