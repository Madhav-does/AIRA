"""
ARIA App Control — Smart Application Launcher
Finds and opens any Windows app using multiple strategies:
  1. Known app map (instant)
  2. Start Menu shortcut search (finds anything installed)
  3. WindowsApps / LOCALAPPDATA paths
  4. Direct ShellExecute fallback
"""

import subprocess
import os
import glob
import shutil

# ── Precise app map (name → what to pass to ShellExecute) ────────────────────
APP_MAP = {
    # Browsers
    'chrome': 'chrome', 'google chrome': 'chrome', 'google': 'chrome',
    'firefox': 'firefox', 'mozilla firefox': 'firefox',
    'edge': 'msedge', 'microsoft edge': 'msedge',
    'opera': 'opera', 'opera gx': 'opera',
    'brave': 'brave',

    # Microsoft Office
    'word': 'winword', 'microsoft word': 'winword',
    'excel': 'excel', 'microsoft excel': 'excel',
    'powerpoint': 'powerpnt', 'microsoft powerpoint': 'powerpnt',
    'onenote': 'onenote', 'outlook': 'outlook',
    'access': 'msaccess',

    # System tools
    'notepad': 'notepad',
    'calculator': 'calc', 'calc': 'calc',
    'paint': 'mspaint',
    'task manager': 'taskmgr', 'taskmgr': 'taskmgr',
    'control panel': 'control',
    'settings': 'ms-settings:',
    'windows settings': 'ms-settings:',
    'snipping tool': 'snippingtool',
    'snip': 'snippingtool',
    'file explorer': 'explorer',
    'explorer': 'explorer', 'files': 'explorer',
    'device manager': 'devmgmt.msc',
    'disk management': 'diskmgmt.msc',
    'registry editor': 'regedit',
    'event viewer': 'eventvwr.msc',
    'msconfig': 'msconfig',

    # Terminals
    'cmd': 'cmd', 'command prompt': 'cmd',
    'powershell': 'powershell',
    'terminal': 'wt', 'windows terminal': 'wt',

    # Media & Music
    'spotify': 'spotify',
    'vlc': 'vlc',
    'media player': 'wmplayer',
    'groove music': 'mswindowsmusic:',
    'photos': 'ms-photos:',
    'movies': 'mswindowsvideo:',

    # Communication
    'discord': 'discord',
    'zoom': 'zoom',
    'teams': 'teams', 'microsoft teams': 'teams',
    'skype': 'skype',
    'telegram': 'telegram',
    'whatsapp': 'whatsapp',

    # Dev
    'vs code': 'code', 'vscode': 'code', 'visual studio code': 'code',
    'android studio': 'studio64',
    'git bash': 'git-bash',
    'warp': 'warp',

    # Games & Launchers
    'steam': 'steam',
    'epic games': 'epicgameslauncher', 'epic': 'epicgameslauncher',
    'roblox': 'roblox',

    # Creative
    'obs': 'obs64', 'obs studio': 'obs64',
    'capcut': 'capcut',
    'streamlabs': 'streamlabs',
    'medal': 'medal',

    # Misc
    'sticky notes': 'stikynot',
    'clock': 'ms-clock:',
    'calendar': 'outlookcal:',
    'maps': 'bingmaps:',
    'store': 'ms-windows-store:',
}

# URI-scheme apps that use os.startfile
URI_APPS = {
    'ms-settings:', 'ms-photos:', 'mswindowsmusic:', 'mswindowsvideo:',
    'ms-clock:', 'outlookcal:', 'bingmaps:', 'ms-windows-store:',
}

# LocalAppData WindowsApps paths (Microsoft Store apps)
_WINAPPS_DIR = os.path.expandvars(r'%LOCALAPPDATA%\Microsoft\WindowsApps')


def _find_in_start_menu(name: str) -> str | None:
    """Search Start Menu .lnk files for the given app name (fuzzy)."""
    dirs = [
        os.path.expandvars(r'%APPDATA%\Microsoft\Windows\Start Menu\Programs'),
        r'C:\ProgramData\Microsoft\Windows\Start Menu\Programs',
    ]
    name_lower = name.lower().strip()
    best = None
    for d in dirs:
        for lnk in glob.glob(os.path.join(d, '**', '*.lnk'), recursive=True):
            stem = os.path.splitext(os.path.basename(lnk))[0].lower()
            if name_lower in stem or stem in name_lower:
                if best is None or len(stem) < len(os.path.splitext(os.path.basename(best))[0]):
                    best = lnk
    return best


def _find_in_winappsfolder(name: str) -> str | None:
    """Check WindowsApps folder for the executable."""
    name_lower = name.lower().replace(' ', '')
    try:
        for exe in glob.glob(os.path.join(_WINAPPS_DIR, '*.exe')):
            stem = os.path.splitext(os.path.basename(exe))[0].lower()
            if name_lower in stem or stem in name_lower:
                return exe
    except Exception:
        pass
    return None


def open_app(name: str) -> bool:
    """
    Open an application by friendly name.
    Tries multiple strategies to guarantee the app is found & launched.
    """
    name_lower = name.lower().strip()
    cmd = APP_MAP.get(name_lower)

    # Strategy 1: Known map
    if cmd:
        return _launch(cmd, name)

    # Strategy 2: Direct executable in PATH
    if shutil.which(name_lower):
        return _launch(name_lower, name)

    # Strategy 3: WindowsApps (Store apps like Spotify)
    win_path = _find_in_winappsfolder(name_lower)
    if win_path:
        return _launch(win_path, name)

    # Strategy 4: Start Menu shortcut
    lnk = _find_in_start_menu(name_lower)
    if lnk:
        return _launch(lnk, name)

    # Strategy 5: Just try it as-is (maybe it's in PATH under a different name)
    return _launch(name_lower, name)


def _launch(cmd: str, display_name: str) -> bool:
    """Actually launch a command / path / URI."""
    try:
        if cmd in URI_APPS or cmd.startswith('ms-') or cmd.startswith('outlook'):
            os.startfile(cmd)
        elif cmd.endswith('.lnk') or os.path.isabs(cmd):
            os.startfile(cmd)
        else:
            subprocess.Popen(
                cmd,
                shell=True,
                creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
            )
        print(f"[AppControl] ✓ Opened '{display_name}' → {cmd}")
        return True
    except Exception as e:
        print(f"[AppControl] ✗ Failed to open '{display_name}': {e}")
        return False


def close_app(name: str) -> bool:
    """Force-close an application by process name."""
    try:
        # Try exact name first, then with .exe
        for proc in [name, f"{name}.exe", f"{name.lower()}.exe"]:
            result = subprocess.run(
                ['taskkill', '/f', '/im', proc],
                creationflags=subprocess.CREATE_NO_WINDOW,
                capture_output=True
            )
            if result.returncode == 0:
                print(f"[AppControl] ✓ Closed '{name}'")
                return True
    except Exception as e:
        print(f"[AppControl] ✗ Failed to close '{name}': {e}")
    return False


def get_running_apps() -> list[str]:
    """Return list of currently running process names."""
    try:
        result = subprocess.run(
            ['tasklist', '/fo', 'csv', '/nh'],
            capture_output=True, text=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        apps = []
        for line in result.stdout.strip().splitlines():
            parts = line.strip('"').split('","')
            if parts:
                apps.append(parts[0].replace('.exe', ''))
        return apps
    except Exception:
        return []
