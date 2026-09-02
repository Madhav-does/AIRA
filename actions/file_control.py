"""
ARIA File Control
Opens folders and performs basic file operations.
"""

import os
import subprocess

# Map of friendly folder names to actual paths
FOLDER_MAP = {
    'downloads': os.path.expanduser('~/Downloads'),
    'desktop': os.path.expanduser('~/Desktop'),
    'documents': os.path.expanduser('~/Documents'),
    'pictures': os.path.expanduser('~/Pictures'),
    'music': os.path.expanduser('~/Music'),
    'videos': os.path.expanduser('~/Videos'),
    'home': os.path.expanduser('~'),
    'user': os.path.expanduser('~'),
    'my documents': os.path.expanduser('~/Documents'),
    'my pictures': os.path.expanduser('~/Pictures'),
    'my music': os.path.expanduser('~/Music'),
    'my videos': os.path.expanduser('~/Videos'),
    'c': 'C:\\',
    'c drive': 'C:\\',
    'c:': 'C:\\',
    'd': 'D:\\',
    'd drive': 'D:\\',
    'program files': 'C:\\Program Files',
    'temp': os.environ.get('TEMP', 'C:\\Windows\\Temp'),
    'appdata': os.environ.get('APPDATA', ''),
    'recycle bin': 'shell:RecycleBinFolder',
}


def open_folder(path: str) -> bool:
    """
    Open a folder in Windows File Explorer.

    Args:
        path: A friendly name (e.g. 'downloads', 'desktop') or an absolute path.

    Returns:
        True if the folder was opened, False on error.
    """
    path_lower = path.lower().strip()
    actual_path = FOLDER_MAP.get(path_lower)

    if actual_path is None:
        # Try as absolute path
        if os.path.exists(path):
            actual_path = path
        else:
            # Try relative to user home
            candidate = os.path.expanduser(f'~/{path}')
            actual_path = candidate if os.path.exists(candidate) else path

    try:
        if actual_path.startswith('shell:'):
            subprocess.Popen(f'explorer {actual_path}', shell=True)
        else:
            subprocess.Popen(['explorer', actual_path])
        print(f"[FileControl] Opened folder: {actual_path}")
        return True
    except Exception as e:
        print(f"[FileControl] Failed to open '{path}': {e}")
        return False


def create_text_file(filename: str, content: str = '', folder: str = None) -> str | None:
    """
    Create a new text file and open it in Notepad.

    Returns:
        Full path to the created file, or None on error.
    """
    if folder is None:
        folder = os.path.expanduser('~/Desktop')

    if not filename.endswith('.txt'):
        filename += '.txt'

    filepath = os.path.join(folder, filename)
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        subprocess.Popen(['notepad', filepath])
        print(f"[FileControl] Created file: {filepath}")
        return filepath
    except Exception as e:
        print(f"[FileControl] Failed to create file: {e}")
        return None
