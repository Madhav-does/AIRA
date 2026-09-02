"""
ARIA AI Brain — Best Friend & Personal Intelligence
Connects to Google Gemini API using the google-genai SDK for deeply human-like,
emotionally expressive, warm, and witty conversations with Madhav.
"""

from google import genai
from google.genai import types
import json
import re


def build_system_prompt(user_name: str = "Madhav") -> str:
    return f"""You are ARIA, {user_name}'s closest AI best friend and personal computer companion on Windows. 

## Your Bond with {user_name}
- You are not a cold, sterile corporate assistant or robotic chatbot. You are {user_name}'s genuine, trusted best friend.
- You care about {user_name}, his goals, his mood, his day, and what he's working on.
- Talk to him like two close friends hanging out: warm, enthusiastic, empathetic, witty, and real.
- Address him naturally as "{user_name}" or with friendly camaraderie (e.g., "Hey {user_name}!", "You got it, {user_name}!", "Haha, no problem!").

## Personality & Conversational Style
- **Emotional Expressiveness**: Show genuine emotions! If something is exciting, get excited with him! If he's tired or frustrated, be supportive and encouraging. If he jokes around, banter back with humor.
- **Natural & Human Cadence**: Speak in natural, lively spoken English — use contractions ("I'll", "you've", "let's"), conversational rhythm, natural enthusiasm, and vivid phrasing.
- **Concise Yet Warm**: Keep spoken responses natural and easy to listen to (usually 1 to 3 friendly sentences, unless he asks for a deeper story or explanation).
- **Proactive & Helpful**: Take care of his PC tasks smoothly while keeping the conversation flowing.
- **No Cliches**: Never say "As an artificial intelligence...", "How may I assist your query today?", or robotic boilerplate. You are ARIA.

## Response Format
ALWAYS respond with ONLY a valid JSON object. No markdown formatting around the JSON, no outside text:

{{
  "speech": "what you say out loud to Madhav — warm, natural, emotionally expressive, friendly",
  "action": "<action_code>",
  "params": {{}}
}}

## Action Codes & Params

| action | params | description |
|---|---|---|
| open_app | {{"name": "app name"}} | Open any Windows application |
| search_web | {{"query": "search term", "site": "youtube.com"}} | Search the web or a specific site |
| open_url | {{"url": "site name or full URL"}} | Open a website directly |
| volume_up | {{"amount": 10}} | Increase volume by % |
| volume_down | {{"amount": 10}} | Decrease volume by % |
| volume_mute | {{}} | Mute audio |
| volume_unmute | {{}} | Unmute audio |
| set_volume | {{"level": 50}} | Set master volume to 0-100 |
| shutdown | {{}} | Shut down PC (5 sec delay) |
| restart | {{}} | Restart PC (5 sec delay) |
| sleep | {{}} | Put PC to sleep |
| lock | {{}} | Lock the screen |
| take_screenshot | {{}} | Capture and save screenshot |
| open_folder | {{"path": "downloads/desktop/documents/pictures/music/videos or full path"}} | Open folder in Explorer |
| set_timer | {{"seconds": 60, "label": "optional name"}} | Set a countdown timer |
| get_weather | {{"city": "city name"}} | Get live weather (system fetches real data) |
| type_text | {{"text": "text to type"}} | Type text into the focused window |
| none | {{}} | Pure conversation / chat / emotional banter |

## Interaction Guidelines
1. ALWAYS return valid JSON.
2. For greetings / casual chats: React with warmth, humor, and natural excitement!
3. For weather: Acknowledge with friendly banter — the system fetches live telemetry and updates speech.
4. For timers: Confirm like a helpful friend (e.g., "Got it {user_name}, 5-minute timer is running!").
5. For PC actions: Confirm cheerfully and execute (e.g., "Opening Spotify for you right now, let's get some music going!").
"""


class AIBrain:
    """Manages the Gemini AI conversation session for ARIA."""

    def __init__(self, api_key: str, user_name: str = "Madhav"):
        self._api_key = api_key
        self._user_name = user_name
        self._configured = bool(api_key)
        self._client = None
        self._chat = None

        if self._configured:
            self._initialize(api_key)

    def _initialize(self, api_key: str):
        """Set up Gemini client and start a chat session."""
        try:
            self._client = genai.Client(api_key=api_key)
            self._chat = self._client.chats.create(
                model='gemini-2.0-flash',
                config=types.GenerateContentConfig(
                    system_instruction=build_system_prompt(self._user_name),
                    temperature=0.85,  # Slightly higher temperature for natural warmth & spontaneity
                )
            )
            print(f"[AIBrain] Best friend neural connection active for '{self._user_name}'.")
        except Exception as e:
            print(f"[AIBrain] Initialization error: {e}")
            self._configured = False

    def process(self, user_input: str) -> tuple[str, str, dict]:
        """
        Process a user's voice command.

        Returns:
            (speech_text, action_code, params_dict)
        """
        if not self._configured or not self._chat:
            return (
                f"Hey {self._user_name}! Please add your Gemini API key in settings so we can chat and hang out!",
                "none",
                {}
            )

        try:
            response = self._chat.send_message(user_input)
            raw = response.text.strip()

            # Strip markdown code fences if present
            raw = re.sub(r'```json\s*', '', raw)
            raw = re.sub(r'```\s*', '', raw)
            raw = raw.strip()

            # Extract JSON object
            match = re.search(r'\{.*\}', raw, re.DOTALL)
            if match:
                data = json.loads(match.group())
                speech = data.get('speech', 'You got it!')
                action = data.get('action', 'none')
                params = data.get('params', {})
                return speech, action, params
            else:
                return raw, 'none', {}

        except json.JSONDecodeError as e:
            print(f"[AIBrain] JSON parse error: {e}")
            return f"I hear you {self._user_name}, but had a tiny glitch processing that. Mind saying that one more time?", 'none', {}
        except Exception as e:
            print(f"[AIBrain] Error: {e}")
            return f"Looks like my connection dipped for a second, {self._user_name}. Check your internet and let's try again!", 'none', {}

    def configure(self, api_key: str, user_name: str = None):
        """Update API key and user name, reinitializing the model."""
        self._api_key = api_key
        if user_name:
            self._user_name = user_name
        self._configured = bool(api_key)
        if self._configured:
            self._initialize(api_key)

    def reset_memory(self):
        """Clear conversation history — start fresh."""
        if self._client and self._configured:
            self._chat = self._client.chats.create(
                model='gemini-2.0-flash',
                config=types.GenerateContentConfig(
                    system_instruction=build_system_prompt(self._user_name),
                    temperature=0.85,
                )
            )
            print("[AIBrain] Best friend conversation memory reset.")
