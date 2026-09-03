"""
ARIA File Browser MCP Server
Browse the filesystem, read files, list directories, search for files.
Tools: list_directory, read_file, search_files, get_file_info
Run as: python mcp_servers/file_browser_server.py
"""

import os
import glob
from datetime import datetime
from mcp.server.mcpserver import MCPServer

mcp = MCPServer("ARIA File Browser")

# Safe roots — only expose these top-level directories
SAFE_ROOTS = [
    os.path.expanduser("~/Desktop"),
    os.path.expanduser("~/Documents"),
    os.path.expanduser("~/Downloads"),
    os.path.expanduser("~/Pictures"),
    os.path.expanduser("~/Music"),
    os.path.expanduser("~/Videos"),
]


def _is_safe(path: str) -> bool:
    """Ensure the resolved path is inside an allowed root."""
    resolved = os.path.realpath(path)
    return any(resolved.startswith(os.path.realpath(r)) for r in SAFE_ROOTS)


def _friendly_size(n: int) -> str:
    for unit in ['B', 'KB', 'MB', 'GB']:
        if n < 1024:
            return f"{n:.0f} {unit}"
        n /= 1024
    return f"{n:.1f} GB"


@mcp.tool()
def list_directory(path: str = "Desktop") -> str:
    """
    List files and folders in a directory.
    Path can be 'Desktop', 'Downloads', 'Documents', 'Pictures', or a full path.
    """
    aliases = {
        'desktop':   os.path.expanduser("~/Desktop"),
        'downloads': os.path.expanduser("~/Downloads"),
        'documents': os.path.expanduser("~/Documents"),
        'pictures':  os.path.expanduser("~/Pictures"),
        'music':     os.path.expanduser("~/Music"),
        'videos':    os.path.expanduser("~/Videos"),
    }
    resolved = aliases.get(path.lower().strip(), path)
    if not _is_safe(resolved):
        return f"Access denied: '{resolved}' is outside allowed directories."
    try:
        entries = os.listdir(resolved)
        lines = []
        for e in sorted(entries)[:40]:
            full = os.path.join(resolved, e)
            if os.path.isdir(full):
                lines.append(f"[DIR]  {e}")
            else:
                sz = _friendly_size(os.path.getsize(full))
                lines.append(f"[FILE] {e} ({sz})")
        total = len(entries)
        result = "\n".join(lines)
        if total > 40:
            result += f"\n... and {total - 40} more"
        return result or "Empty directory."
    except Exception as e:
        return f"Error listing '{resolved}': {e}"


@mcp.tool()
def read_file(path: str) -> str:
    """
    Read the contents of a text file.
    Only works for .txt, .md, .json, .csv, .py, .js, .html, .log files under safe roots.
    """
    ALLOWED_EXT = {'.txt', '.md', '.json', '.csv', '.py', '.js', '.html', '.log', '.yaml', '.yml'}
    if not _is_safe(path):
        return "Access denied."
    if os.path.splitext(path)[1].lower() not in ALLOWED_EXT:
        return "File type not allowed for reading."
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read(4000)  # cap at 4000 chars
        return content if content else "(empty file)"
    except Exception as e:
        return f"Error reading file: {e}"


@mcp.tool()
def search_files(query: str, directory: str = "Desktop", extension: str = "") -> str:
    """
    Search for files by name in a directory.
    query: filename keyword to search for
    directory: 'Desktop', 'Downloads', 'Documents', etc.
    extension: optional file extension filter e.g. 'pdf', 'txt'
    """
    aliases = {
        'desktop':   os.path.expanduser("~/Desktop"),
        'downloads': os.path.expanduser("~/Downloads"),
        'documents': os.path.expanduser("~/Documents"),
        'pictures':  os.path.expanduser("~/Pictures"),
    }
    root = aliases.get(directory.lower().strip(), os.path.expanduser("~/Desktop"))
    if not _is_safe(root):
        return "Access denied."

    pattern = f"**/*{query}*"
    if extension:
        ext = extension.lstrip('.')
        pattern = f"**/*{query}*.{ext}"

    try:
        matches = glob.glob(os.path.join(root, pattern), recursive=True)[:20]
        if not matches:
            return f"No files found matching '{query}'."
        lines = []
        for m in matches:
            rel = os.path.relpath(m, root)
            sz  = _friendly_size(os.path.getsize(m)) if os.path.isfile(m) else "DIR"
            lines.append(f"{rel} ({sz})")
        return "\n".join(lines)
    except Exception as e:
        return f"Search error: {e}"


@mcp.tool()
def get_file_info(path: str) -> str:
    """Get detailed metadata for a file: size, created date, modified date."""
    if not _is_safe(path):
        return "Access denied."
    try:
        stat = os.stat(path)
        size    = _friendly_size(stat.st_size)
        created = datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M")
        modified= datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
        return (
            f"File: {os.path.basename(path)}\n"
            f"Size: {size}\n"
            f"Created: {created}\n"
            f"Modified: {modified}"
        )
    except Exception as e:
        return f"Error: {e}"


if __name__ == "__main__":
    mcp.run(transport='stdio')
