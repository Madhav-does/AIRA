"""
ARIA System Info MCP Server
Exposes live PC info as MCP tools: running processes, disk space, network stats.
Tools: get_running_processes, get_disk_usage, get_system_info, kill_process_by_name
Run as: python mcp_servers/system_info_server.py
"""

import subprocess
import os
import shutil
from mcp.server.fastmcp import FastMCP

try:
    import psutil
    PSUTIL = True
except ImportError:
    PSUTIL = False

mcp = FastMCP("ARIA System Info")


@mcp.tool()
def get_running_processes(filter_name: str = "") -> str:
    """Get a list of currently running processes. Optionally filter by name."""
    try:
        result = subprocess.run(
            ['tasklist', '/fo', 'csv', '/nh'],
            capture_output=True, text=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        lines = []
        for line in result.stdout.strip().splitlines()[:30]:
            parts = line.strip('"').split('","')
            if len(parts) >= 2:
                name = parts[0]
                mem  = parts[4] if len(parts) > 4 else '?'
                if not filter_name or filter_name.lower() in name.lower():
                    lines.append(f"{name} ({mem})")
        return "\n".join(lines) if lines else "No matching processes."
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def get_disk_usage() -> str:
    """Get disk space usage for all drives."""
    lines = []
    if PSUTIL:
        for part in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(part.mountpoint)
                pct   = usage.percent
                free  = usage.free // (1024**3)
                total = usage.total // (1024**3)
                lines.append(f"{part.device}: {total - free}GB used / {total}GB total ({pct}% full)")
            except PermissionError:
                continue
    else:
        total, used, free = shutil.disk_usage("C:\\")
        lines.append(f"C:\\: {used//1024**3}GB used / {total//1024**3}GB total")
    return "\n".join(lines) if lines else "Could not read disk info."


@mcp.tool()
def get_system_info() -> str:
    """Get live CPU usage, RAM usage, and uptime."""
    if not PSUTIL:
        return "psutil not available."
    cpu   = psutil.cpu_percent(interval=0.5)
    ram   = psutil.virtual_memory()
    boot  = psutil.boot_time()
    import time
    up_s  = int(time.time() - boot)
    up_h  = up_s // 3600
    up_m  = (up_s % 3600) // 60
    return (
        f"CPU: {cpu}%\n"
        f"RAM: {ram.used // 1024**3}GB used / {ram.total // 1024**3}GB total ({ram.percent}%)\n"
        f"Uptime: {up_h}h {up_m}m"
    )


@mcp.tool()
def kill_process_by_name(process_name: str) -> str:
    """Force-kill a running process by name (e.g. 'notepad.exe' or 'chrome')."""
    for name in [process_name, f"{process_name}.exe"]:
        result = subprocess.run(
            ['taskkill', '/f', '/im', name],
            capture_output=True, text=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        if result.returncode == 0:
            return f"Process '{name}' terminated."
    return f"Could not find process '{process_name}'."


if __name__ == "__main__":
    mcp.run(transport='stdio')
