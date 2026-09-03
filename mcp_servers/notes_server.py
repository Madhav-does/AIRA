"""
ARIA Notes MCP Server
A lightweight personal notes server. Stores notes in a local JSON file.
Tools: add_note, get_notes, search_notes, delete_note
Run as: python mcp_servers/notes_server.py
"""

import json
import os
from datetime import datetime
from mcp.server.mcpserver import MCPServer

NOTES_FILE = os.path.join(os.path.dirname(__file__), '..', 'aria_notes.json')

mcp = MCPServer("ARIA Notes")


def _load() -> list[dict]:
    try:
        with open(NOTES_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _save(notes: list[dict]):
    with open(NOTES_FILE, 'w') as f:
        json.dump(notes, f, indent=2)


@mcp.tool()
def add_note(content: str, tag: str = "general") -> str:
    """Add a personal note. Content is the note text, tag is a category like 'work', 'idea', 'todo'."""
    notes = _load()
    note = {
        "id": len(notes) + 1,
        "content": content,
        "tag": tag,
        "created": datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    notes.append(note)
    _save(notes)
    return f"Note saved: '{content}' (tag: {tag})"


@mcp.tool()
def get_notes(tag: str = "", limit: int = 5) -> str:
    """Get recent notes. Optionally filter by tag. Returns the most recent notes."""
    notes = _load()
    if tag:
        notes = [n for n in notes if n.get('tag', '').lower() == tag.lower()]
    recent = notes[-limit:][::-1]
    if not recent:
        return "No notes found."
    lines = [f"[{n['id']}] ({n['tag']}) {n['content']} — {n['created']}" for n in recent]
    return "\n".join(lines)


@mcp.tool()
def search_notes(query: str) -> str:
    """Search notes by keyword. Returns all notes containing the query text."""
    notes = _load()
    matches = [n for n in notes if query.lower() in n['content'].lower()]
    if not matches:
        return f"No notes found matching '{query}'."
    lines = [f"[{n['id']}] ({n['tag']}) {n['content']} — {n['created']}" for n in matches]
    return "\n".join(lines)


@mcp.tool()
def delete_note(note_id: int) -> str:
    """Delete a note by its ID number."""
    notes = _load()
    original_count = len(notes)
    notes = [n for n in notes if n.get('id') != note_id]
    if len(notes) == original_count:
        return f"No note found with ID {note_id}."
    _save(notes)
    return f"Note {note_id} deleted."


if __name__ == "__main__":
    mcp.run(transport='stdio')
