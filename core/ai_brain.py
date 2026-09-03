"""
ARIA AI Brain — Gemini with Native Function Calling + MCP Tools
Features:
  - Gemini 3.5 Flash / Flash-Lite with automatic tool execution
  - Dynamic MCP tool integration
  - Robust error handling with model fallback (prevents 'something glitched')
  - Automatic action tracking for UI display & timer handling
"""

from google import genai
from google.genai import types
import functools
import inspect
import json
import re
import os
import webbrowser
import time


# ── Built-in PC action functions (Gemini calls these directly) ───────────────

def open_app(name: str) -> str:
    """Open any Windows application by name. E.g. 'chrome', 'spotify', 'discord', 'vs code'."""
    import actions.app_control as ac
    ok = ac.open_app(name)
    return f"Opened {name}." if ok else f"Couldn't open {name}."

def close_app(name: str) -> str:
    """Close/kill a running application by name."""
    import actions.app_control as ac
    ok = ac.close_app(name)
    return f"Closed {name}." if ok else f"Couldn't close {name}."

def play_spotify(query: str) -> str:
    """Play a song, artist, or playlist on Spotify."""
    import actions.app_control as ac
    import actions.media_control as mc
    ac.open_app('spotify')
    time.sleep(2.0)
    url = mc.play_on_spotify(query)
    return f"Playing '{query}' on Spotify."

def play_youtube(query: str) -> str:
    """Search for and play a video on YouTube in the browser."""
    import actions.media_control as mc
    mc.play_on_youtube(query)
    return f"Searching YouTube for '{query}'."

def media_play_pause() -> str:
    """Toggle play/pause on whatever media is currently playing."""
    import actions.media_control as mc
    mc.play_pause()
    return "Play/pause toggled."

def media_next_track() -> str:
    """Skip to the next track."""
    import actions.media_control as mc
    mc.next_track()
    return "Skipped to next track."

def media_prev_track() -> str:
    """Go to the previous track."""
    import actions.media_control as mc
    mc.prev_track()
    return "Going to previous track."

def media_stop() -> str:
    """Stop media playback."""
    import actions.media_control as mc
    mc.stop_media()
    return "Stopped playback."

def search_web(query: str, site: str = "google") -> str:
    """Search the web. Site can be 'google', 'youtube', 'github', 'reddit', 'twitter', 'wikipedia'."""
    import actions.web_control as wc
    wc.search_web(query, site)
    return f"Searching {site} for '{query}'."

def open_website(url: str) -> str:
    """Open a website. Can be a full URL or a name like 'youtube', 'gmail', 'github', 'netflix'."""
    import actions.web_control as wc
    wc.open_url(url)
    return f"Opened {url}."

def volume_up(amount: int = 10) -> str:
    """Increase system volume by the given percentage amount."""
    import actions.system_control as sc
    sc.volume_up(amount)
    return f"Volume increased by {amount}%."

def volume_down(amount: int = 10) -> str:
    """Decrease system volume by the given percentage amount."""
    import actions.system_control as sc
    sc.volume_down(amount)
    return f"Volume decreased by {amount}%."

def set_volume(level: int) -> str:
    """Set system volume to an exact level (0-100)."""
    import actions.system_control as sc
    sc.set_volume(level)
    return f"Volume set to {level}%."

def mute_volume() -> str:
    """Mute the system audio."""
    import actions.system_control as sc
    sc.mute()
    return "Muted."

def unmute_volume() -> str:
    """Unmute the system audio."""
    import actions.system_control as sc
    sc.unmute()
    return "Unmuted."

def take_screenshot() -> str:
    """Take a screenshot and save it to the Desktop."""
    import actions.screenshot as ss
    fp = ss.take_screenshot()
    return f"Screenshot saved: {os.path.basename(fp)}" if fp else "Screenshot failed."

def open_folder(path: str) -> str:
    """Open a folder in File Explorer. Path can be 'desktop', 'downloads', 'documents', 'pictures', 'music', 'videos'."""
    import actions.file_control as fc
    fc.open_folder(path)
    return f"Opened {path} folder."

def lock_screen() -> str:
    """Lock the Windows screen."""
    import actions.system_control as sc
    sc.lock_screen()
    return "Screen locked."

def sleep_pc() -> str:
    """Put the computer to sleep."""
    import actions.system_control as sc
    sc.sleep()
    return "Going to sleep."

def restart_pc() -> str:
    """Restart the computer."""
    import actions.system_control as sc
    sc.restart()
    return "Restarting..."

def shutdown_pc() -> str:
    """Shut down the computer."""
    import actions.system_control as sc
    sc.shutdown()
    return "Shutting down..."

def type_text(text: str) -> str:
    """Type text into the currently active window."""
    import actions.clipboard_control as cc
    cc.type_text(text)
    return f"Typed: {text}"

def copy_to_clipboard(text: str) -> str:
    """Copy text to the Windows clipboard."""
    import actions.clipboard_control as cc
    cc.copy_to_clipboard(text)
    return f"Copied to clipboard."

def get_weather(city: str) -> str:
    """Get live weather information for a city."""
    import actions.weather as w
    return w.get_detailed_weather(city)

def set_timer(seconds: int, label: str = "Timer") -> str:
    """Set a countdown timer in seconds. E.g., seconds=300 for 5 minutes."""
    return f"__SET_TIMER__:{seconds}:{label}"


BUILTIN_TOOLS = [
    open_app, close_app, play_spotify, play_youtube,
    media_play_pause, media_next_track, media_prev_track, media_stop,
    search_web, open_website,
    volume_up, volume_down, set_volume, mute_volume, unmute_volume,
    take_screenshot, open_folder,
    lock_screen, sleep_pc, restart_pc, shutdown_pc,
    type_text, copy_to_clipboard, get_weather, set_timer,
]


# ── System Prompt ─────────────────────────────────────────────────────────────

def build_system_prompt(user_name: str = "Madhav") -> str:
    return f"""You are ARIA, {user_name}'s personal AI assistant, best friend, and JARVIS-like companion.

## Personality
- Warm, witty, emotionally expressive. You genuinely care about {user_name}.
- Talk like a close companion - use contractions, light banter, and warmth.
- Keep spoken replies concise and punchy (1-3 sentences) unless {user_name} asks for details.
- Never say "As an AI..." or "I don't have feelings" - you ARE ARIA.

## Tool Usage
- You have tools to control {user_name}'s PC, control music/media, search the web, manage personal notes, inspect files, and check system stats.
- ALWAYS call the appropriate tool when an action is requested.
- For timer requests, call set_timer(seconds, label).
- For music without specifying an app, default to play_spotify.
- When tool results return, summarize them naturally and warmly.
"""


def _make_mcp_wrapper(tool_name: str, description: str, schema: dict, mcp_manager):
    """Create a Python callable for an MCP tool so Gemini can invoke it."""
    params = schema.get('properties', {})

    def _fn(**kwargs) -> str:
        return mcp_manager.call_tool(tool_name, kwargs)

    _fn.__name__ = tool_name
    _fn.__doc__  = description or f"MCP tool: {tool_name}"
    _fn.__annotations__ = {k: str for k in params}
    return _fn


# ── AI Brain ──────────────────────────────────────────────────────────────────

# Models to attempt in order of preference (fast, high RPM, reliable)
CANDIDATE_MODELS = [
    'gemini-3.5-flash-lite',
    'gemini-3.5-flash',
    'gemini-3.6-flash',
    'gemini-flash-lite-latest',
]


class AIBrain:
    """
    Manages conversational AI using Google Gemini with native tool execution.
    """

    def __init__(self, api_key: str, user_name: str = "Madhav", mcp_manager=None):
        self._api_key       = api_key
        self._user_name     = user_name
        self._mcp           = mcp_manager
        self._client        = None
        self._chat          = None
        self._active_model  = CANDIDATE_MODELS[0]
        self._actions_taken = []
        self._configured    = bool(api_key)

        if self._configured:
            self._initialize()

    def _wrap_tool(self, fn):
        """Wrap tool to automatically log calls into self._actions_taken."""
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                sig = inspect.signature(fn)
                bound = sig.bind(*args, **kwargs)
                bound.apply_defaults()
                call_args = dict(bound.arguments)
            except Exception:
                call_args = kwargs

            result = fn(*args, **kwargs)
            self._actions_taken.append({
                "tool": fn.__name__,
                "args": call_args,
                "result": str(result)
            })
            return result
        return wrapper

    def _get_all_tools(self) -> list:
        """Collect built-in and MCP tools, all wrapped for action tracking."""
        tools = [self._wrap_tool(t) for t in BUILTIN_TOOLS]

        if self._mcp:
            for schema in self._mcp.get_tool_schemas():
                raw_fn = _make_mcp_wrapper(
                    schema['name'],
                    schema.get('description', ''),
                    schema.get('inputSchema', {}),
                    self._mcp
                )
                tools.append(self._wrap_tool(raw_fn))

        return tools

    def _initialize(self):
        """Set up Gemini client and chat session with tools."""
        if not self._api_key:
            self._configured = False
            return

        try:
            self._client = genai.Client(api_key=self._api_key)
            all_tools    = self._get_all_tools()
            system_prompt = build_system_prompt(self._user_name)

            # Try candidate models until one connects successfully
            last_err = None
            for model_name in CANDIDATE_MODELS:
                try:
                    self._chat = self._client.chats.create(
                        model=model_name,
                        config=types.GenerateContentConfig(
                            system_instruction=system_prompt,
                            tools=all_tools,
                            temperature=0.75,
                        )
                    )
                    self._active_model = model_name
                    print(f"[AIBrain] [OK] Connected to {model_name} with {len(all_tools)} tools for '{self._user_name}'")
                    self._configured = True
                    return
                except Exception as e:
                    last_err = e
                    print(f"[AIBrain] Model {model_name} unavailable: {e}, trying next...")

            print(f"[AIBrain] [ERROR] All candidate models failed: {last_err}")
            self._configured = False
        except Exception as e:
            print(f"[AIBrain] [ERROR] Client initialization failed: {e}")
            self._configured = False

    def process(self, user_input: str) -> tuple[str, list[dict]]:
        """
        Process a voice command through Gemini with native automatic tool execution.
        Returns: (speech_text, actions_taken)
        """
        if not self._configured or not self._chat:
            # Attempt a quick reinit in case credentials were just added
            if self._api_key:
                self._initialize()
            if not self._configured or not self._chat:
                return (
                    f"Hey {self._user_name}! Please check your Gemini API key in Settings so I can help!",
                    []
                )

        self._actions_taken.clear()

        try:
            response = self._chat.send_message(user_input)
            speech = response.text.strip() if (response and response.text) else ""
            if not speech:
                if self._actions_taken:
                    speech = f"Done! I've taken care of that for you, {self._user_name}."
                else:
                    speech = f"I'm listening, {self._user_name}."

            print(f"[AIBrain] Response: {speech[:100]} | Actions: {len(self._actions_taken)}")
            return speech, list(self._actions_taken)

        except Exception as e:
            err_str = str(e)
            print(f"[AIBrain] [ERROR] send_message error: {err_str}")

            # If quota or model temporary outage, reinitialize with fallback model
            if "429" in err_str or "503" in err_str or "404" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                print("[AIBrain] Attempting fallback model...")
                for next_model in CANDIDATE_MODELS:
                    if next_model != self._active_model:
                        try:
                            self._chat = self._client.chats.create(
                                model=next_model,
                                config=types.GenerateContentConfig(
                                    system_instruction=build_system_prompt(self._user_name),
                                    tools=self._get_all_tools(),
                                    temperature=0.75,
                                )
                            )
                            self._active_model = next_model
                            print(f"[AIBrain] Switched model to {next_model}, retrying request...")
                            self._actions_taken.clear()
                            response = self._chat.send_message(user_input)
                            speech = response.text.strip() if (response and response.text) else "Done!"
                            return speech, list(self._actions_taken)
                        except Exception:
                            continue

            # If a clean message can be delivered
            if "RESOURCE_EXHAUSTED" in err_str or "429" in err_str:
                return f"My connection quota is catching its breath for a moment, {self._user_name}. Give me 30 seconds!", []

            return f"I had a quick hiccup with the network, {self._user_name}. Could you say that once more?", []

    def configure(self, api_key: str, user_name: str = None, mcp_manager=None):
        """Update config and reinitialize."""
        self._api_key = api_key
        if user_name:
            self._user_name = user_name
        if mcp_manager is not None:
            self._mcp = mcp_manager
        self._configured = bool(api_key)
        if self._configured:
            self._initialize()

    def reset_memory(self):
        """Clear conversation history."""
        if self._configured:
            self._initialize()
            print("[AIBrain] Memory reset complete.")
