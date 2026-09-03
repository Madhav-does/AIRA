"""
ARIA App Control — Smart Application Launcher
Finds and opens any Windows app using multiple robust strategies:
  1. Windows Registry App Paths (official way Windows Run launches Chrome, Edge, Code, etc.)
  2. Start Menu .lnk scan (finds literally every installed application)
  3. LocalAppData WindowsApps (UWP / Microsoft Store apps like Spotify, WhatsApp)
  4. Known explicit paths / URI protocols
  5. ShellExecute via os.startfile
  6. Subprocess fallback
"""

import subprocess
import os
import glob
import shutil
import winreg

# Known explicit paths / URIs for instant launch
EXPLICIT_PATHS = {
    'chrome': [
        r'C:\Program Files\Google\Chrome\Application\chrome.exe',
        r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
        os.path.expandvars(r'%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe'),
    ],
    'edge': [
        r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
        r'C:\Program Files\Microsoft\Edge\Application\msedge.exe',
    ],
    'spotify': [
        os.path.expandvars(r'%LOCALAPPDATA%\Microsoft\WindowsApps\Spotify.exe'),
        os.path.expandvars(r'%APPDATA%\Spotify\Spotify.exe'),
    ],
    'discord': [
        os.path.expandvars(r'%LOCALAPPDATA%\Discord\Update.exe --processStart Discord.exe'),
        os.path.expandvars(r'%APPDATA%\Microsoft\Windows\Start Menu\Programs\Discord Inc\Discord.lnk'),
    ],
    'vs code': [
        os.path.expandvars(r'%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe'),
        r'C:\Program Files\Microsoft VS Code\Code.exe',
    ],
}

# Friendly name mappings
APP_MAP = {
    # Browsers
    'chrome': 'chrome', 'google chrome': 'chrome', 'google': 'chrome',
    'firefox': 'firefox', 'mozilla firefox': 'firefox',
    'edge': 'msedge', 'microsoft edge': 'msedge',
    'opera': 'opera', 'opera gx': 'opera',
    'brave': 'brave',

    # Office
    'word': 'winword', 'microsoft word': 'winword',
    'excel': 'excel', 'microsoft excel': 'excel',
    'powerpoint': 'powerpnt', 'microsoft powerpoint': 'powerpnt',
    'onenote': 'onenote', 'outlook': 'outlook',

    # System tools
    'notepad': 'notepad',
    'calculator': 'calc', 'calc': 'calc',
    'paint': 'mspaint',
    'task manager': 'taskmgr', 'taskmgr': 'taskmgr',
    'control panel': 'control',
    'settings': 'ms-settings:', 'windows settings': 'ms-settings:',
    'snipping tool': 'snippingtool', 'snip': 'snippingtool',
    'file explorer': 'explorer', 'explorer': 'explorer', 'files': 'explorer',
    'cmd': 'cmd', 'command prompt': 'cmd',
    'powershell': 'powershell',
    'terminal': 'wt', 'windows terminal': 'wt',

    # Music & Media
    'spotify': 'spotify',
    'vlc': 'vlc',
    'media player': 'wmplayer',
    'photos': 'ms-photos:',

    # Dev & Communication
    'discord': 'discord',
    'whatsapp': 'whatsapp',
    'zoom': 'zoom',
    'teams': 'teams',
    'vs code': 'code', 'vscode': 'code', 'visual studio code': 'code',
    'git bash': 'git-bash',
    'warp': 'warp',

    # Games
    'steam': 'steam',
    'epic games': 'epicgameslauncher',
    'roblox': 'roblox',

    # Creative
    'capcut': 'capcut',
    'obs': 'obs64',
    'streamlabs': 'streamlabs',
    'medal': 'medal',
}

_WINAPPS_DIR = os.path.expandvars(r'%LOCALAPPDATA%\Microsoft\WindowsApps')


def _find_in_registry_app_paths(name: str) -> str | None:
    """Check HKLM and HKCU App Paths for the executable path."""
    name_clean = name.lower().strip()
    candidates = [name_clean]
    if not name_clean.endswith('.exe'):
        candidates.append(f"{name_clean}.exe")

    for root in [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]:
        base_key = r'SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths'
        for cand in candidates:
            try:
                sub_key = f"{base_key}\\{cand}"
                with winreg.OpenKey(root, sub_key) as key:
                    val, _ = winreg.QueryValueEx(key, '')
                    clean_val = val.strip('"').strip("'")
                    if clean_val and os.path.exists(clean_val):
                        return clean_val
            except OSError:
                pass
    return None


def _find_in_start_menu(name: str) -> str | None:
    """Search Start Menu .lnk shortcuts for the given name."""
    dirs = [
        os.path.expandvars(r'%APPDATA%\Microsoft\Windows\Start Menu\Programs'),
        r'C:\ProgramData\Microsoft\Windows\Start Menu\Programs',
    ]
    name_clean = name.lower().replace(' ', '').replace('-', '').strip()
    best = None

    for d in dirs:
        if not os.path.exists(d):
            continue
        for lnk in glob.glob(os.path.join(d, '**', '*.lnk'), recursive=True):
            stem = os.path.splitext(os.path.basename(lnk))[0].lower()
            stem_clean = stem.replace(' ', '').replace('-', '')
            if name_clean in stem_clean or stem_clean in name_clean:
                if best is None or len(stem) < len(os.path.splitext(os.path.basename(best))[0]):
                    best = lnk
    return best


def _find_in_winappsfolder(name: str) -> str | None:
    """Check WindowsApps folder for Microsoft Store executables."""
    name_clean = name.lower().replace(' ', '').replace('-', '')
    try:
        for exe in glob.glob(os.path.join(_WINAPPS_DIR, '*.exe')):
            stem = os.path.splitext(os.path.basename(exe))[0].lower()
            stem_clean = stem.replace(' ', '').replace('-', '')
            if name_clean in stem_clean or stem_clean in name_clean:
                return exe
    except Exception:
        pass
    return None


def open_app(name: str) -> bool:
    """
    Open an application by friendly name.
    Tries 6 distinct strategies to guarantee it launches.
    """
    if not name:
        return False

    name_lower = name.lower().strip()
    canonical = APP_MAP.get(name_lower, name_lower)

    # Strategy 1: Check known explicit filesystem paths
    for key in [name_lower, canonical]:
        if key in EXPLICIT_PATHS:
            for p in EXPLICIT_PATHS[key]:
                if os.path.exists(p.split()[0]):  # handles args like Update.exe
                    return _launch(p, name)

    # Strategy 2: Windows Registry App Paths (finds Chrome, Edge, VS Code, etc.)
    for test_name in [canonical, name_lower]:
        reg_path = _find_in_registry_app_paths(test_name)
        if reg_path:
            return _launch(reg_path, name)

    # Strategy 3: Start Menu shortcuts (.lnk files)
    for test_name in [name, canonical, name_lower]:
        lnk = _find_in_start_menu(test_name)
        if lnk and os.path.exists(lnk):
            return _launch(lnk, name)

    # Strategy 4: WindowsApps folder (Store apps like Spotify)
    for test_name in [canonical, name_lower]:
        win_app = _find_in_winappsfolder(test_name)
        if win_app and os.path.exists(win_app):
            return _launch(win_app, name)

    # Strategy 5: URI protocol schemes (ms-settings:, spotify:, etc.)
    if ':' in canonical and not os.path.splitdrive(canonical)[0]:
        return _launch(canonical, name)

    # Strategy 6: ShellExecute / PATH / direct execution
    return _launch(canonical, name)


def _launch(target: str, display_name: str) -> bool:
    """Execute target using the most appropriate Windows launcher."""
    try:
        # Check if target is a protocol URI or direct file
        if (':' in target and not os.path.splitdrive(target)[0]) or os.path.exists(target):
            os.startfile(target)
            print(f"[AppControl] [OK] Opened '{display_name}' via os.startfile -> {target}")
            return True

        # Try os.startfile with .exe extension (ShellExecute will look up App Paths)
        for ext_target in [target, f"{target}.exe"]:
            try:
                os.startfile(ext_target)
                print(f"[AppControl] [OK] Opened '{display_name}' via ShellExecute -> {ext_target}")
                return True
            except OSError:
                pass

        # Subprocess detached launch
        subprocess.Popen(
            f'start "" "{target}"',
            shell=True,
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        )
        print(f"[AppControl] [OK] Launched '{display_name}' -> {target}")
        return True

    except Exception as e:
        print(f"[AppControl] [ERROR] Failed to open '{display_name}': {e}")
        return False


def close_app(name: str) -> bool:
    """Force-close an application by process name."""
    try:
        targets = [name, f"{name}.exe", f"{name.lower()}.exe"]
        for proc in targets:
            result = subprocess.run(
                ['taskkill', '/f', '/im', proc],
                creationflags=subprocess.CREATE_NO_WINDOW,
                capture_output=True
            )
            if result.returncode == 0:
                print(f"[AppControl] [OK] Closed '{name}'")
                return True
    except Exception as e:
        print(f"[AppControl] [ERROR] Failed to close '{name}': {e}")
    return False


def get_running_apps() -> list[str]:
    """Return list of running processes."""
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
