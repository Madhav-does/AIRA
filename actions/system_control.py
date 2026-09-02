"""
ARIA System Control
Controls Windows system functions: volume, power, and screen lock.
Uses pycaw for precise volume control with a graceful fallback.
"""

import os
import subprocess

# ── Volume Control (pycaw) ───────────────────────────────────────────────────
try:
    from ctypes import cast, POINTER
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    PYCAW_AVAILABLE = True
except ImportError:
    PYCAW_AVAILABLE = False
    print("[SystemControl] pycaw not available — volume control will be limited.")


def _get_volume_interface():
    """Get the Windows audio endpoint volume interface."""
    if not PYCAW_AVAILABLE:
        return None
    try:
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        return cast(interface, POINTER(IAudioEndpointVolume))
    except AttributeError:
        # Newer pycaw changed the AudioDevice API — use IMMDeviceEnumerator directly
        try:
            from ctypes import POINTER, cast
            from comtypes import CLSCTX_ALL
            import comtypes.client
            MMDeviceApiLib = comtypes.client.GetModule(
                ["{2FDAAFA3-7523-4F66-9957-9D5E7FE698F6}", 1, 0]
            )
            IMMDeviceEnumerator = MMDeviceApiLib.IMMDeviceEnumerator
            enum = comtypes.CoCreateInstance(
                MMDeviceApiLib.MMDeviceEnumerator,
                IMMDeviceEnumerator,
                comtypes.CLSCTX_INPROC_SERVER
            )
            device = enum.GetDefaultAudioEndpoint(0, 1)  # eRender, eConsole
            interface = device.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            return cast(interface, POINTER(IAudioEndpointVolume))
        except Exception as e2:
            print(f"[SystemControl] Volume interface fallback error: {e2}")
            return None
    except Exception as e:
        print(f"[SystemControl] Volume interface error: {e}")
        return None



def get_volume_level() -> int:
    """Return current master volume level (0–100)."""
    vol = _get_volume_interface()
    if vol:
        try:
            return round(vol.GetMasterVolumeLevelScalar() * 100)
        except Exception:
            pass
    return 50


def set_volume(level: int) -> bool:
    """Set master volume to a specific level (0–100)."""
    level = max(0, min(100, level))
    vol = _get_volume_interface()
    if vol:
        try:
            vol.SetMasterVolumeLevelScalar(level / 100.0, None)
            print(f"[SystemControl] Volume set to {level}%")
            return True
        except Exception as e:
            print(f"[SystemControl] Set volume error: {e}")
    return False


def volume_up(amount: int = 10) -> bool:
    """Increase volume by a given percentage."""
    current = get_volume_level()
    return set_volume(current + amount)


def volume_down(amount: int = 10) -> bool:
    """Decrease volume by a given percentage."""
    current = get_volume_level()
    return set_volume(current - amount)


def mute() -> bool:
    """Mute the system audio."""
    vol = _get_volume_interface()
    if vol:
        try:
            vol.SetMute(1, None)
            print("[SystemControl] Muted.")
            return True
        except Exception:
            pass
    return False


def unmute() -> bool:
    """Unmute the system audio."""
    vol = _get_volume_interface()
    if vol:
        try:
            vol.SetMute(0, None)
            print("[SystemControl] Unmuted.")
            return True
        except Exception:
            pass
    return False


# ── Power Management ──────────────────────────────────────────────────────────

def shutdown():
    """Shut down the PC with a 5-second delay (allows ARIA to finish speaking)."""
    print("[SystemControl] Shutdown initiated.")
    os.system('shutdown /s /t 5')


def restart():
    """Restart the PC with a 5-second delay."""
    print("[SystemControl] Restart initiated.")
    os.system('shutdown /r /t 5')


def sleep():
    """Put the PC into sleep/suspend mode."""
    print("[SystemControl] Sleep initiated.")
    os.system('rundll32.exe powrprof.dll,SetSuspendState 0,1,0')


def lock_screen():
    """Lock the Windows user session."""
    print("[SystemControl] Locking screen.")
    import ctypes
    ctypes.windll.user32.LockWorkStation()
