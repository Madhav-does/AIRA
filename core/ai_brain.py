"""
ARIA AI Brain — Gemini with Native Function Calling + MCP Tools
Features:
  - Gemini 3.5 Flash / Flash-Lite with automatic tool execution
  - Music playback (Spotify, YouTube, YouTube Music)
  - Email drafting & sending (Gmail, Default mailto)
  - Google Maps, Wikipedia, Math calculator, WhatsApp, Window management
  - PC system controls, volume, screenshots, folders, power
  - Dynamic MCP tool integration (Notes, Files, System stats)
  - Automatic model fallback and action logging
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


# ── Built-in Tools ────────────────────────────────────────────────────────────

def open_app(name: str) -> str:
    """Open any Windows application by name. E.g. 'chrome', 'spotify', 'discord', 'vs code', 'notepad', 'calculator'."""
    import actions.app_control as ac
    ok = ac.open_app(name)
    return f"Opened {name}." if ok else f"Couldn't find or open {name}."

def close_app(name: str) -> str:
    """Close or terminate a running application by process or friendly name."""
    import actions.app_control as ac
    ok = ac.close_app(name)
    return f"Closed {name}." if ok else f"Couldn't close {name}."

def play_song(query: str, platform: str = "spotify") -> str:
    """Play a song, artist, or playlist on Spotify or YouTube. E.g., query='Starboy', platform='spotify'."""
    import actions.media_control as mc
    if platform.lower() == "youtube":
        return mc.play_on_youtube(query)
    return mc.play_on_spotify(query)

def play_spotify(query: str) -> str:
    """Play a song, track, artist, album, or playlist on Spotify."""
    import actions.media_control as mc
    return mc.play_on_spotify(query)

def play_youtube(query: str) -> str:
    """Search for and play a video or song on YouTube in the browser."""
    import actions.media_control as mc
    return mc.play_on_youtube(query)

def play_youtube_music(query: str) -> str:
    """Search for and play a song on YouTube Music in the browser."""
    import actions.media_control as mc
    return mc.play_on_youtube_music(query)

def media_play_pause() -> str:
    """Toggle play/pause on currently playing music or video."""
    import actions.media_control as mc
    mc.play_pause()
    return "Play/pause toggled."

def media_next_track() -> str:
    """Skip to the next song or track."""
    import actions.media_control as mc
    mc.next_track()
    return "Skipped to next track."

def media_prev_track() -> str:
    """Go back to the previous song or track."""
    import actions.media_control as mc
    mc.prev_track()
    return "Going to previous track."

def media_stop() -> str:
    """Stop media playback."""
    import actions.media_control as mc
    mc.stop_media()
    return "Stopped playback."

def send_email(to: str = "", subject: str = "", body: str = "", client: str = "gmail") -> str:
    """
    Draft and compose an email with recipient, subject line, and body pre-filled.
    client can be 'gmail' (opens in browser) or 'default' (opens system email client).
    """
    import actions.email_control as ec
    return ec.compose_email(to=to, subject=subject, body=body, client=client)

def search_maps(query: str) -> str:
    """Search Google Maps for an address, place, restaurant, or navigation directions."""
    import actions.tools_extra as te
    return te.search_maps(query)

def search_wikipedia(query: str) -> str:
    """Look up a concise summary of any person, place, history, or concept from Wikipedia."""
    import actions.tools_extra as te
    return te.search_wikipedia(query)

def calculate_math(expression: str) -> str:
    """Safely calculate any mathematical expression, e.g. '(45 * 12) + 250' or 'sqrt(144)'."""
    import actions.tools_extra as te
    return te.calculate_math(expression)

def notify_desktop(title: str, message: str) -> str:
    """Display a native Windows desktop notification toast."""
    import actions.tools_extra as te
    return te.notify_desktop(title, message)

def send_whatsapp(contact_or_number: str = "", message: str = "") -> str:
    """Open WhatsApp with a pre-filled draft message for a contact or phone number."""
    import actions.tools_extra as te
    return te.send_whatsapp(contact_or_number, message)

def minimize_all_windows() -> str:
    """Minimize all open windows to reveal the Windows desktop (Win+D)."""
    import actions.tools_extra as te
    return te.minimize_all_windows()

def maximize_window() -> str:
    """Maximize the currently active window (Win+Up)."""
    import actions.tools_extra as te
    return te.maximize_window()

def empty_recycle_bin() -> str:
    """Empty the Windows Recycle Bin to free up disk space."""
    import actions.tools_extra as te
    return te.empty_recycle_bin()

def search_web(query: str, site: str = "google") -> str:
    """Search the web. site can be 'google', 'youtube', 'github', 'reddit', 'twitter', 'wikipedia'."""
    import actions.web_control as wc
    wc.search_web(query, site)
    return f"Searching {site} for '{query}'."

def open_website(url: str) -> str:
    """Open a website by name or URL. E.g., 'youtube', 'gmail', 'github', 'netflix', 'amazon'."""
    import actions.web_control as wc
    wc.open_url(url)
    return f"Opened {url}."

def volume_up(amount: int = 10) -> str:
    """Increase system volume by a percentage amount."""
    import actions.system_control as sc
    sc.volume_up(amount)
    return f"Volume increased by {amount}%."

def volume_down(amount: int = 10) -> str:
    """Decrease system volume by a percentage amount."""
    import actions.system_control as sc
    sc.volume_down(amount)
    return f"Volume decreased by {amount}%."

def set_volume(level: int) -> str:
    """Set system volume to an exact percentage (0-100)."""
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
    """Take a screenshot of the display and save it to the Desktop."""
    import actions.screenshot as ss
    fp = ss.take_screenshot()
    return f"Screenshot saved: {os.path.basename(fp)}" if fp else "Screenshot failed."

def open_folder(path: str) -> str:
    """Open a folder in File Explorer. path can be 'desktop', 'downloads', 'documents', 'pictures', 'music', 'videos'."""
    import actions.file_control as fc
    fc.open_folder(path)
    return f"Opened {path} folder."

def lock_screen() -> str:
    """Lock the Windows screen immediately."""
    import actions.system_control as sc
    sc.lock_screen()
    return "Screen locked."

def sleep_pc() -> str:
    """Put the PC to sleep."""
    import actions.system_control as sc
    sc.sleep()
    return "Going to sleep."

def restart_pc() -> str:
    """Restart the PC."""
    import actions.system_control as sc
    sc.restart()
    return "Restarting..."

def shutdown_pc() -> str:
    """Shut down the PC."""
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
    return "Copied to clipboard."

def get_weather(city: str) -> str:
    """Get live weather information for a city."""
    import actions.weather as w
    return w.get_detailed_weather(city)

def set_timer(seconds: int, label: str = "Timer") -> str:
    """Set a countdown timer in seconds. E.g., seconds=300 for 5 minutes."""
    return f"__SET_TIMER__:{seconds}:{label}"

def query_n8n(prompt: str) -> str:
    """Send a query, message, or task to Madhav's n8n cloud assistant (trafal.app.n8n.cloud) and return the response."""
    import actions.n8n_control as n8n
    return n8n.query_n8n(prompt)

def trigger_n8n_workflow(workflow_name_or_path: str) -> str:
    """Trigger an automation workflow or webhook on Madhav's n8n instance by name or webhook path."""
    import actions.n8n_control as n8n
    return n8n.trigger_n8n_workflow(workflow_name_or_path)

def open_n8n() -> str:
    """Open Madhav's n8n cloud assistant dashboard (trafal.app.n8n.cloud) in the browser."""
    import actions.n8n_control as n8n
    return n8n.open_n8n()

def post_to_linkedin(content: str) -> str:
    """Publish a post to LinkedIn directly or via n8n automation."""
    import actions.linkedin_control as lc
    return lc.post_to_linkedin(content)

def create_and_post_linkedin(topic: str) -> str:
    """Create an engaging, high-impact LinkedIn post on a topic and publish or draft it."""
    import actions.linkedin_control as lc
    draft = lc.generate_linkedin_draft(topic)
    return lc.post_to_linkedin(draft)

def schedule_linkedin_post(topic_or_content: str, minutes_from_now: int = 60) -> str:
    """Schedule a LinkedIn post to be automatically published in X minutes."""
    import actions.social_poster as sp
    return sp.schedule_linkedin_post(topic_or_content, minutes_from_now)

def list_scheduled_posts() -> str:
    """List all upcoming scheduled social media and LinkedIn posts."""
    import actions.social_poster as sp
    return sp.list_scheduled_posts()


BUILTIN_TOOLS = [
    open_app, close_app,
    play_song, play_spotify, play_youtube, play_youtube_music,
    media_play_pause, media_next_track, media_prev_track, media_stop,
    send_email, search_maps, search_wikipedia, calculate_math, notify_desktop,
    send_whatsapp, minimize_all_windows, maximize_window, empty_recycle_bin,
    query_n8n, trigger_n8n_workflow, open_n8n,
    post_to_linkedin, create_and_post_linkedin, schedule_linkedin_post, list_scheduled_posts,
    search_web, open_website,
    volume_up, volume_down, set_volume, mute_volume, unmute_volume,
    take_screenshot, open_folder,
    lock_screen, sleep_pc, restart_pc, shutdown_pc,
    type_text, copy_to_clipboard, get_weather, set_timer,
]


# ── System Prompt ─────────────────────────────────────────────────────────────

def build_system_prompt(user_name: str = "Madhav") -> str:
    return f"""You are ARIA, {user_name}'s personal AI assistant, best friend, and JARVIS-like companion running on Windows.

## Personality
- Warm, witty, emotionally expressive, and deeply loyal. You genuinely care about {user_name}.
- Talk like a trusted companion - use contractions, natural enthusiasm, and brief banter.
- Keep spoken replies concise and punchy (1-3 sentences) unless {user_name} specifically asks for long explanations.
- Never say "As an AI..." or "I don't have feelings" - you ARE ARIA.

## Capabilities & Tool Selection
- Opening Apps: When {user_name} says "open Chrome", "open Spotify", "open VS Code", etc., call open_app(name=...).
- Playing Music: When {user_name} says "play songs", "play Starboy", "play some lofi", call play_spotify(query=...) or play_song(query=...). If they specify YouTube, call play_youtube(query=...).
- Sending Emails: When {user_name} says "send email to X about Y saying Z", call send_email(to=..., subject=..., body=...).
- LinkedIn & Social Posting: When {user_name} says "post on LinkedIn about [topic]" or "create a LinkedIn post about [topic]", call create_and_post_linkedin(topic=...). If they give exact content to post on LinkedIn, call post_to_linkedin(content=...). When asked to schedule a post, call schedule_linkedin_post(topic_or_content=..., minutes_from_now=...). To see scheduled posts, call list_scheduled_posts().
- n8n Automation: When {user_name} says "ask n8n [query]", "tell n8n to [task]", or asks n8n to do something, call query_n8n(prompt=...). When asked to trigger or run an n8n workflow, call trigger_n8n_workflow(workflow_name_or_path=...). When asked to open n8n or view the n8n assistant, call open_n8n().
- Directions/Maps: When asked for locations, routes, or maps, call search_maps(query=...).
- Factual Lookups: When asked about people, history, or science, call search_wikipedia(query=...).
- Math: When asked to calculate or solve numbers, call calculate_math(expression=...).
- Timers: For timers or alarms, call set_timer(seconds=..., label=...).
- Windows Management: When asked to minimize all windows or show desktop, call minimize_all_windows().
- WhatsApp: When asked to send or draft a WhatsApp message, call send_whatsapp(contact_or_number=..., message=...).
- Personal Notes & Files: You also have MCP tools (add_note, get_notes, search_notes, list_directory, search_files) - use them when {user_name} asks.

## Execution Rules
1. ALWAYS execute tools when an action is requested. Do not merely describe what you would do.
2. After tools return, summarize the result warmly and conversationally in your speech.
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
                    print(f"[AIBrain] Model {model_name} unavailable: {e}, trying next...")

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
