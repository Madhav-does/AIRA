"""
ARIA App Control
Opens and closes Windows applications by name.
"""

import subprocess
import os

# Map of friendly names → executable commands
APP_MAP = {
    # Browsers
    'chrome': 'chrome',
    'google chrome': 'chrome',
    'firefox': 'firefox',
    'edge': 'msedge',
    'microsoft edge': 'msedge',
    'brave': 'brave',
    'opera': 'opera',

    # Productivity
    'notepad': 'notepad',
    'notepad++': 'notepad++',
    'word': 'winword',
    'microsoft word': 'winword',
    'excel': 'excel',
    'microsoft excel': 'excel',
    'powerpoint': 'powerpnt',
    'microsoft powerpoint': 'powerpnt',
    'onenote': 'onenote',
    'outlook': 'outlook',

    # System tools
    'calculator': 'calc',
    'paint': 'mspaint',
    'file explorer': 'explorer',
    'explorer': 'explorer',
    'task manager': 'taskmgr',
    'control panel': 'control',
    'settings': 'ms-settings:',
    'windows settings': 'ms-settings:',
    'snipping tool': 'snippingtool',
    'snip': 'snippingtool',

    # Terminals
    'command prompt': 'cmd',
    'cmd': 'cmd',
    'terminal': 'wt',
    'windows terminal': 'wt',
    'powershell': 'powershell',

    # Media & Entertainment
    'vlc': 'vlc',
    'spotify': 'spotify',
    'media player': 'wmplayer',
    'windows media player': 'wmplayer',

    # Communication
    'discord': 'discord',
    'zoom': 'zoom',
    'teams': 'teams',
    'microsoft teams': 'teams',
    'skype': 'skype',
    'whatsapp': 'whatsapp',
    'telegram': 'telegram',

    # Dev tools
    'vs code': 'code',
    'visual studio code': 'code',
    'vscode': 'code',
    'git bash': 'git-bash',
    'android studio': 'studio64',

    # Other
    'steam': 'steam',
    'epic games': 'epicgameslauncher',
    'obs': 'obs64',
}

# Apps that use the ms- URI scheme (opened via os.startfile)
MS_URI_APPS = {'ms-settings:'}


def open_app(name: str) -> bool:
    """
    Open an application by friendly name or executable name.

    Args:
        name: App name (e.g. "Chrome", "Notepad", "VS Code")

    Returns:
        True if launch was attempted, False on error.
    """
    name_lower = name.lower().strip()
    cmd = APP_MAP.get(name_lower, name_lower)

    try:
        if cmd in MS_URI_APPS or cmd.startswith('ms-'):
            os.startfile(cmd)
        else:
            subprocess.Popen(cmd, shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
        print(f"[AppControl] Opened: {name} → '{cmd}'")
        return True
    except Exception as e:
        print(f"[AppControl] Failed to open '{name}': {e}")
        return False


def close_app(name: str) -> bool:
    """
    Force-close an application by process name.

    Args:
        name: Process name without .exe (e.g. "notepad", "chrome")
    """
    try:
        subprocess.run(
            ['taskkill', '/f', '/im', f'{name}.exe'],
            creationflags=subprocess.CREATE_NO_WINDOW,
            capture_output=True
        )
        print(f"[AppControl] Closed: {name}")
        return True
    except Exception as e:
        print(f"[AppControl] Failed to close '{name}': {e}")
        return False
