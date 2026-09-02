#!/usr/bin/env python3
"""
ARIA — Adaptive Real-time Intelligent Assistant
Main entry point and orchestrator.

Usage:
    python main.py
"""

import sys
import os
import threading

# ── Suppress noisy startup messages ──────────────────────────────────────────
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

# ── Imports ───────────────────────────────────────────────────────────────────
import config as cfg
from core.voice_input import VoiceInput
from core.voice_output import VoiceOutput
from core.ai_brain import AIBrain
from core.hotkey_handler import HotkeyHandler
from ui.app_window import AppWindow

import actions.app_control as app_control
import actions.system_control as system_control
import actions.web_control as web_control
import actions.file_control as file_control
import actions.weather as weather_module
import actions.screenshot as screenshot_module
from actions.timer_control import TimerManager


class ARIAAssistant:
    """
    Top-level orchestrator that wires together voice I/O, AI brain, PC actions,
    hotkey handling, and the floating UI.
    """

    def __init__(self):
        # Load user settings
        self.config = cfg.load_config()

        # ── Core components ──────────────────────────────────────────────────
        self.voice_input = VoiceInput(
            language=self.config.get('stt_language', 'en-IN')
        )
        self.voice_output = VoiceOutput(
            voice=self.config.get('voice_name', 'en-US-GuyNeural'),
            speed=self.config.get('voice_speed', 175),
            volume=self.config.get('voice_volume', 0.9)
        )
        self.ai_brain = AIBrain(
            self.config.get('gemini_api_key', ''),
            user_name=self.config.get('user_name', 'Madhav')
        )
        self.timer_manager = TimerManager()

        # ── State ────────────────────────────────────────────────────────────
        self._busy = False          # Prevents overlapping listen sessions
        self._busy_lock = threading.Lock()

        # ── UI ───────────────────────────────────────────────────────────────
        self.window = AppWindow(
            config=self.config,
            on_listen_request=self._start_listening,
            on_api_key_save=self._on_settings_saved,
            on_reset_memory=self._reset_memory,
        )

        # Connect TTS status to UI updates
        self.voice_output.set_callbacks(
            on_start=lambda: self.window.set_status('speaking'),
            on_finish=lambda: self.window.set_status('idle'),
        )

        # ── Hotkeys ───────────────────────────────────────────────────────────
        self.hotkey = HotkeyHandler(
            talk_hotkey=self.config.get('hotkey', 'P'),
            summon_hotkey=self.config.get('summon_hotkey', 'ctrl+space'),
            on_talk=self._start_listening,
            on_summon=self.window.toggle_visibility,
        )

    # ── Startup ───────────────────────────────────────────────────────────────

    def _startup_tasks(self):
        """
        Runs in a background thread after the UI is visible.
        Calibrates mic, starts hotkey listener, speaks greeting.
        """
        # Mic calibration
        self.window.add_system_message("Calibrating acoustic sensors...")
        self.voice_input.calibrate()
        self.window.add_system_message("Sensors nominal. Neural core linked.")

        # Start global hotkeys
        self.hotkey.start()

        # Personalized Best Friend Greeting
        user_name = self.config.get('user_name', 'Madhav')
        if not self.config.get('gemini_api_key'):
            msg = f"Hey {user_name}! I'm ARIA! Drop your free Gemini API key in settings and we're good to go!"
            self.window.add_system_message("⚠️ No API key set. Open ⚙ Settings and add your Gemini API key.")
        else:
            msg = f"Hey {user_name}! I'm so glad you're here. Everything is up and running smoothly! How can I help you today, my friend?"

        self.voice_output.speak(msg)
        self.window.add_aria_message(msg)

    # ── Main Listen → Think → Act → Speak Loop ────────────────────────────────

    def _start_listening(self):
        """
        Entry point for each voice interaction.
        Called from hotkey handler or mic button — already in a background thread.
        """
        # Ensure ARIA surfaces to the front when triggered
        self.window.bring_to_front()

        # Prevent re-entrance
        with self._busy_lock:
            if self._busy:
                return
            self._busy = True

        try:
            self._run_interaction()
        finally:
            with self._busy_lock:
                self._busy = False

    def _run_interaction(self):
        """Full pipeline: listen → AI → action → speak."""

        # 1 ── LISTEN
        self.window.set_status('listening')
        text = self.voice_input.listen(timeout=7, phrase_time_limit=15)

        if not text:
            user_name = self.config.get('user_name', 'Madhav')
            self.window.set_status('idle')
            self.window.add_system_message("No clear audio captured. Please speak closer to your microphone.")
            self.voice_output.speak(f"I didn't quite catch that, {user_name} — mind saying that again?")
            return

        self.window.add_user_message(text)

        # 2 ── THINK (AI)
        self.window.set_status('thinking')
        speech, action, params = self.ai_brain.process(text)

        # 3 ── HANDLE WEATHER (real data replaces AI placeholder)
        if action == 'get_weather':
            city = params.get('city', '') or self.config.get('weather_city', '')
            weather_text = weather_module.get_detailed_weather(city)
            speech = f"Here's the weather: {weather_text}"

        # 4 ── EXECUTE PC ACTION
        self._execute_action(action, params)

        # 5 ── SPEAK + SHOW response
        self.window.add_aria_message(speech)
        self.voice_output.speak(speech)

    def _execute_action(self, action: str, params: dict):
        """Dispatch a PC action based on the AI's decision."""
        try:
            if action == 'open_app':
                app_control.open_app(params.get('name', ''))

            elif action == 'search_web':
                web_control.search_web(params.get('query', ''), params.get('site', ''))

            elif action == 'open_url':
                web_control.open_url(params.get('url', ''))

            elif action == 'volume_up':
                system_control.volume_up(int(params.get('amount', 10)))

            elif action == 'volume_down':
                system_control.volume_down(int(params.get('amount', 10)))

            elif action == 'volume_mute':
                system_control.mute()

            elif action == 'volume_unmute':
                system_control.unmute()

            elif action == 'set_volume':
                system_control.set_volume(int(params.get('level', 50)))

            elif action == 'shutdown':
                system_control.shutdown()

            elif action == 'restart':
                system_control.restart()

            elif action == 'sleep':
                system_control.sleep()

            elif action == 'lock':
                system_control.lock_screen()

            elif action == 'take_screenshot':
                filepath = screenshot_module.take_screenshot()
                if filepath:
                    self.window.add_system_message(f"Screenshot saved → {os.path.basename(filepath)}")

            elif action == 'open_folder':
                file_control.open_folder(params.get('path', 'desktop'))

            elif action == 'set_timer':
                seconds = int(params.get('seconds', 60))
                label = params.get('label', 'Timer')

                def _timer_done(lbl):
                    msg = f"Your {lbl} is done!"
                    self.voice_output.speak(msg)
                    self.window.add_aria_message(msg)

                self.timer_manager.set_timer(seconds, label, on_complete=_timer_done)

            elif action == 'type_text':
                import pyautogui
                import time
                time.sleep(0.4)  # Let window focus settle
                pyautogui.typewrite(params.get('text', ''), interval=0.04)

            elif action in ('none', 'get_weather'):
                pass  # Conversation only or already handled above

            else:
                print(f"[ARIA] Unknown action: '{action}'")

        except Exception as e:
            print(f"[ARIA] Action error ({action}): {e}")
            self.window.add_system_message(f"Action failed: {e}")

    # ── Settings & Memory ─────────────────────────────────────────────────────

    def _on_settings_saved(self, new_config: dict):
        """Apply updated settings at runtime."""
        self.config.update(new_config)
        cfg.save_config(self.config)

        self.ai_brain.configure(
            self.config.get('gemini_api_key', ''),
            user_name=self.config.get('user_name', 'Madhav')
        )
        self.hotkey.update_hotkeys(
            new_talk_hotkey=self.config.get('hotkey', 'P'),
            new_summon_hotkey=self.config.get('summon_hotkey', 'ctrl+space')
        )
        self.voice_input.set_language(self.config.get('stt_language', 'en-IN'))
        self.voice_output.set_voice(self.config.get('voice_name', 'en-US-GuyNeural'))
        self.voice_output.set_speed(self.config.get('voice_speed', 175))

        print("[ARIA] Settings updated.")

    def _reset_memory(self):
        self.ai_brain.reset_memory()

    # ── Run ───────────────────────────────────────────────────────────────────

    def run(self):
        """Start ARIA. Blocks until the window is closed."""
        # Launch startup tasks after UI is ready
        threading.Thread(target=self._startup_tasks, daemon=True, name="ARIA-Startup").start()

        # Run the UI event loop (main thread)
        self.window.run()

        # Cleanup on exit
        self.hotkey.stop()
        self.voice_output.stop()
        print("[ARIA] Shutting down. Goodbye!")


# ── Entry Point ───────────────────────────────────────────────────────────────

def main():
    print("=" * 50)
    print("  ARIA — Adaptive Real-time Intelligent Assistant")
    print("=" * 50)

    try:
        aria = ARIAAssistant()
        aria.run()
    except KeyboardInterrupt:
        print("\n[ARIA] Interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"[ARIA] Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
