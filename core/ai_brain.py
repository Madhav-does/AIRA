"""
ARIA AI Brain — Gemini 2.0 Flash with Native Function Calling + MCP Tools
Full agentic loop: Gemini calls tools (PC actions + MCP), gets results, speaks.
"""

from google import genai
from google.genai import types
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
    time.sleep(2.5)
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
    """
    Search the web. Site can be 'google', 'youtube', 'github', 'reddit', 'twitter', 'wikipedia'.
    """
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
    """Set system volume to an exact level (0–100)."""
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
    """
    Open a folder in File Explorer.
    Path can be 'desktop', 'downloads', 'documents', 'pictures', 'music', 'videos'.
    """
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
    """Set a countdown timer. Will alert when done. seconds=60 for 1 minute."""
    # Timer is handled externally by main.py — return intent
    return f"__SET_TIMER__:{seconds}:{label}"


# All built-in tools for Gemini
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
- Talk like a close mate — use contractions, humour, banter.
- Keep speech short and punchy (1–3 sentences) unless asked for detail.
- Never say "As an AI..." — you ARE ARIA.

## How You Work
- You have access to tools that control {user_name}'s Windows PC, play music, browse files, manage notes, and more.
- When a user makes a request, call the right tool(s). You can call multiple tools in sequence.
- After tool results come back, craft a natural spoken response.
- For timer requests use set_timer(). For weather use get_weather().
- If no tool is needed, just respond naturally.

## Rules
1. Always call tools when the user wants an action — never just describe what you'd do.
2. Be conversational and warm in your spoken responses.
3. If something fails, acknowledge it naturally and suggest an alternative.
4. For "play X" without specifying an app, default to Spotify.
5. You also have personal note tools and file browser tools — use them when Madhav asks.
"""


# ── MCP Tool Wrapper (wraps MCP tools as Python callables for Gemini) ─────────

def _make_mcp_wrapper(tool_name: str, description: str, schema: dict, mcp_manager):
    """Create a Python function that calls an MCP tool, for Gemini's tool-use."""
    # Build a dynamic function with the right signature
    params = schema.get('properties', {})
    required = schema.get('required', [])

    def _fn(**kwargs) -> str:
        return mcp_manager.call_tool(tool_name, kwargs)

    _fn.__name__ = tool_name
    _fn.__doc__  = description

    # Annotate for Gemini's introspection
    _fn.__annotations__ = {k: str for k in params}
    return _fn


# ── AI Brain ──────────────────────────────────────────────────────────────────

class AIBrain:
    """
    Manages the Gemini AI conversation for ARIA.
    Uses native function calling for an agentic tool-use loop.
    """

    def __init__(self, api_key: str, user_name: str = "Madhav", mcp_manager=None):
        self._api_key    = api_key
        self._user_name  = user_name
        self._mcp        = mcp_manager
        self._client     = None
        self._chat       = None
        self._configured = bool(api_key)

        if self._configured:
            self._initialize()

    def _get_all_tools(self) -> list:
        """Collect built-in tools + MCP tool wrappers."""
        tools = list(BUILTIN_TOOLS)

        if self._mcp:
            for schema in self._mcp.get_tool_schemas():
                wrapper = _make_mcp_wrapper(
                    schema['name'],
                    schema['description'],
                    schema.get('inputSchema', {}),
                    self._mcp,
                )
                tools.append(wrapper)

        return tools

    def _initialize(self):
        """Set up Gemini client and chat with all tools registered."""
        try:
            self._client = genai.Client(api_key=self._api_key)
            all_tools    = self._get_all_tools()
            print(f"[AIBrain] Tools loaded: {len(all_tools)} "
                  f"({len(BUILTIN_TOOLS)} built-in + "
                  f"{len(all_tools) - len(BUILTIN_TOOLS)} MCP)")

            self._chat = self._client.chats.create(
                model='gemini-2.0-flash',
                config=types.GenerateContentConfig(
                    system_instruction=build_system_prompt(self._user_name),
                    tools=all_tools,
                    temperature=0.80,
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(
                        disable=True   # We handle the loop manually for control
                    ),
                )
            )
            print(f"[AIBrain] ✓ Ready for '{self._user_name}'")
        except Exception as e:
            print(f"[AIBrain] ✗ Init error: {e}")
            import traceback; traceback.print_exc()
            self._configured = False

    def process(self, user_input: str) -> tuple[str, list[dict]]:
        """
        Process a voice command through the full agentic loop.
        Returns: (speech_text, actions_taken)
        actions_taken is a list of {tool, args, result} dicts.
        """
        if not self._configured or not self._chat:
            return (
                f"Hey {self._user_name}! Add your Gemini API key in Settings so I can help!",
                []
            )

        actions_taken = []
        all_tools     = self._get_all_tools()
        tool_map      = {fn.__name__: fn for fn in all_tools}

        try:
            response = self._chat.send_message(user_input)

            # Agentic loop — keep calling tools until Gemini gives a text response
            for _ in range(8):   # max 8 tool-call rounds
                fn_calls = []
                text_parts = []

                for part in response.candidates[0].content.parts:
                    if hasattr(part, 'function_call') and part.function_call:
                        fn_calls.append(part.function_call)
                    elif hasattr(part, 'text') and part.text:
                        text_parts.append(part.text)

                if not fn_calls:
                    # No more tool calls — we have the final speech
                    speech = " ".join(text_parts).strip()
                    if not speech:
                        speech = "Done!"
                    print(f"[AIBrain] Speech: {speech[:80]}")
                    return speech, actions_taken

                # Execute all function calls in this round
                fn_response_parts = []
                for fc in fn_calls:
                    tool_name = fc.name
                    args      = dict(fc.args) if fc.args else {}
                    print(f"[AIBrain] → Calling tool: {tool_name}({args})")

                    fn = tool_map.get(tool_name)
                    if fn:
                        try:
                            result = fn(**args)
                        except Exception as e:
                            result = f"Tool error: {e}"
                    elif self._mcp and self._mcp.has_tool(tool_name):
                        result = self._mcp.call_tool(tool_name, args)
                    else:
                        result = f"Unknown tool: {tool_name}"

                    print(f"[AIBrain] ← Result: {str(result)[:100]}")
                    actions_taken.append({"tool": tool_name, "args": args, "result": str(result)})

                    fn_response_parts.append(
                        types.Part(
                            function_response=types.FunctionResponse(
                                name=tool_name,
                                response={"result": str(result)},
                            )
                        )
                    )

                # Send all results back to Gemini
                response = self._chat.send_message(fn_response_parts)

            return "I got a bit turned around there. Try asking again?", actions_taken

        except Exception as e:
            print(f"[AIBrain] Error: {e}")
            import traceback; traceback.print_exc()
            return f"Something glitched on my end, {self._user_name}. Try again!", []

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
            print("[AIBrain] Memory reset.")
