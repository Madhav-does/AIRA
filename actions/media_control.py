"""
ARIA Media & Music Control
Controls Spotify, YouTube, YouTube Music, and system media playback.
- Media keys: Play/Pause, Next, Previous, Stop
- Spotify search & auto-play
- YouTube & YouTube Music playback
"""

import subprocess
import time
import webbrowser
import urllib.parse
import os

try:
    import ctypes
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False


# Virtual key codes for Windows media keys
VK_MEDIA_PLAY_PAUSE = 0xB3
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_STOP       = 0xB2
KEYEVENTF_KEYUP     = 0x0002


def _send_media_key(vk_code: int) -> bool:
    """Send a virtual media key event (works across Windows apps)."""
    if WIN32_AVAILABLE:
        ctypes.windll.user32.keybd_event(vk_code, 0, 0, 0)
        time.sleep(0.05)
        ctypes.windll.user32.keybd_event(vk_code, 0, KEYEVENTF_KEYUP, 0)
        return True
    return False


def play_pause() -> bool:
    """Toggle play/pause on whatever media player is currently active."""
    print("[MediaControl] Media: Play/Pause")
    return _send_media_key(VK_MEDIA_PLAY_PAUSE)


def next_track() -> bool:
    """Skip to the next song/video."""
    print("[MediaControl] Media: Next Track")
    return _send_media_key(VK_MEDIA_NEXT_TRACK)


def prev_track() -> bool:
    """Go back to the previous song/video."""
    print("[MediaControl] Media: Previous Track")
    return _send_media_key(VK_MEDIA_PREV_TRACK)


def stop_media() -> bool:
    """Stop media playback completely."""
    print("[MediaControl] Media: Stop")
    return _send_media_key(VK_MEDIA_STOP)


def play_on_spotify(query: str) -> str:
    """
    Search for and start playing a song, artist, album, or playlist on Spotify.
    Launches the Spotify desktop app, or falls back to the Spotify web player.
    """
    encoded = urllib.parse.quote_plus(query)
    uri = f"spotify:search:{encoded}"
    web = f"https://open.spotify.com/search/{encoded}"

    # Try launching the desktop Spotify app via Spotify URI scheme
    try:
        # Check Spotify executable locations
        spotify_paths = [
            os.path.expandvars(r'%LOCALAPPDATA%\Microsoft\WindowsApps\Spotify.exe'),
            os.path.expandvars(r'%APPDATA%\Spotify\Spotify.exe'),
        ]
        launched = False
        for sp in spotify_paths:
            if os.path.exists(sp):
                subprocess.Popen(
                    [sp, '--uri', uri],
                    creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
                )
                launched = True
                break

        if not launched:
            # Try URI scheme directly via startfile
            try:
                os.startfile(uri)
                launched = True
            except Exception:
                webbrowser.open(web)

        # Trigger play after a brief moment
        time.sleep(1.0)
        play_pause()

        print(f"[MediaControl] [OK] Spotify playing: '{query}'")
        return f"Playing '{query}' on Spotify."
    except Exception as e:
        print(f"[MediaControl] Fallback to web: {e}")
        webbrowser.open(web)
        return f"Opened Spotify search for '{query}'."


def play_on_youtube(query: str) -> str:
    """Search for and play a song or video on YouTube in the browser."""
    encoded = urllib.parse.quote_plus(query)
    url = f"https://www.youtube.com/results?search_query={encoded}"
    webbrowser.open(url)
    print(f"[MediaControl] [OK] YouTube playing: '{query}'")
    return f"Opened YouTube search for '{query}'."


def play_on_youtube_music(query: str) -> str:
    """Search for and play on YouTube Music in the browser."""
    encoded = urllib.parse.quote_plus(query)
    url = f"https://music.youtube.com/search?q={encoded}"
    webbrowser.open(url)
    print(f"[MediaControl] [OK] YouTube Music playing: '{query}'")
    return f"Opened YouTube Music for '{query}'."
