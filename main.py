#!/usr/bin/env python3
"""
ARIA — Adaptive Real-time Intelligent Assistant
Main orchestrator: wires voice I/O, AI brain, all PC actions, hotkeys, and UI.
"""

import sys
import os
import threading
import time

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import config as cfg
from core.voice_input   import VoiceInput
from core.voice_output  import VoiceOutput
from core.ai_brain      import AIBrain
from core.hotkey_handler import HotkeyHandler
from ui.app_window      import AppWindow

import actions.app_control      as app_ctrl
import actions.system_control   as sys_ctrl
import actions.web_control      as web_ctrl
import actions.file_control     as file_ctrl
import actions.media_control    as media_ctrl
import actions.clipboard_control as clip_ctrl
import actions.weather          as weather_mod
import actions.screenshot       as screenshot_mod
from actions.timer_control import TimerManager


class ARIAAssistant:
    """
    Top-level orchestrator.
    """

    def __init__(self):
        self.config = cfg.load_config()

        # ── Core components ──────────────────────────────────────────────────
        self.voice_input = VoiceInput(
            language=self.config.get('stt_language', 'en-IN')
        )
        self.voice_output = VoiceOutput(
            voice=self.config.get('voice_name', 'en-GB-RyanNeural'),
            speed=self.config.get('voice_speed', 175),
            volume=self.config.get('voice_volume', 0.9)
        )
        self.ai_brain = AIBrain(
            self.config.get('gemini_api_key', ''),
            user_name=self.config.get('user_name', 'Madhav')
        )
        self.timer_manager = TimerManager()

        # ── State ────────────────────────────────────────────────────────────
        self._busy      = False
        self._busy_lock = threading.Lock()

        # ── UI ───────────────────────────────────────────────────────────────
        self.window = AppWindow(
            config=self.config,
            on_listen_request=self._start_listening,
            on_api_key_save=self._on_settings_saved,
            on_reset_memory=self._reset_memory,
        )

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
        """Background startup: calibrate mic, start hotkeys, greet."""
        self.window.add_system_message("Calibrating acoustic sensors...")
        self.voice_input.calibrate()
        self.window.add_system_message("Sensors nominal. All systems online.")

        self.hotkey.start()

        user = self.config.get('user_name', 'Madhav')
        if not self.config.get('gemini_api_key'):
            msg = (f"Hey {user}! I'm ARIA and I'm ready to roll. "
                   f"Just drop your Gemini API key in Settings and we're set!")
            self.window.add_system_message("⚠️ No API key — open ⚙ Settings to add your Gemini key.")
        else:
            msg = (f"Hey {user}! ARIA online, all systems nominal. "
                   f"Press {self.config.get('hotkey','P').upper()} or just click Activate — what can I do for you?")

        self.window.add_aria_message(msg)
        self.voice_output.speak(msg)

    # ── Main Voice Loop ───────────────────────────────────────────────────────

    def _start_listening(self):
        """Entry point for each voice interaction (called from hotkey / button)."""
        self.window.bring_to_front()

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

        # 1. LISTEN
        self.window.set_status('listening')
        text = self.voice_input.listen(timeout=8, phrase_time_limit=15)

        if not text:
            user = self.config.get('user_name', 'Madhav')
            self.window.set_status('idle')
            self.window.add_system_message("No clear audio captured.")
            self.voice_output.speak(
                f"I didn't catch that, {user}. Try speaking a bit louder or closer to the mic?"
            )
            return

        self.window.add_user_message(text)
        print(f"[ARIA] Heard: '{text}'")

        # 2. THINK
        self.window.set_status('thinking')
        speech, action, params = self.ai_brain.process(text)

        # 3. WEATHER override (fetch real data)
        if action == 'get_weather':
            city = params.get('city', '') or self.config.get('weather_city', '')
            weather_text = weather_mod.get_detailed_weather(city)
            speech = f"Here's the latest: {weather_text}"

        # 4. EXECUTE
        self._execute_action(action, params)

        # 5. SPEAK
        self.window.add_aria_message(speech)
        self.voice_output.speak(speech)

    # ── Action Dispatcher ─────────────────────────────────────────────────────

    def _execute_action(self, action: str, params: dict):
        """Dispatch any action from the AI brain to the right handler."""
        try:
            print(f"[ARIA] Executing action: '{action}' params: {params}")

            # ── Apps ──────────────────────────────────────────────────────────
            if action == 'open_app':
                app_ctrl.open_app(params.get('name', ''))

            elif action == 'close_app':
                app_ctrl.close_app(params.get('name', ''))

            # ── Media ─────────────────────────────────────────────────────────
            elif action == 'play_spotify':
                query = params.get('query', '')
                if query:
                    # First open Spotify if not running
                    app_ctrl.open_app('spotify')
                    time.sleep(2.5)  # Let Spotify open
                    media_ctrl.play_on_spotify(query)
                else:
                    media_ctrl.play_pause()

            elif action == 'play_youtube':
                query = params.get('query', '')
                if query:
                    media_ctrl.play_on_youtube(query)
                else:
                    web_ctrl.open_url('youtube')

            elif action == 'media_play_pause':
                media_ctrl.play_pause()

            elif action == 'media_next':
                media_ctrl.next_track()

            elif action == 'media_prev':
                media_ctrl.prev_track()

            elif action == 'media_stop':
                media_ctrl.stop_media()

            # ── Web ───────────────────────────────────────────────────────────
            elif action == 'search_web':
                web_ctrl.search_web(params.get('query', ''), params.get('site', ''))

            elif action == 'open_url':
                web_ctrl.open_url(params.get('url', ''))

            # ── Volume ────────────────────────────────────────────────────────
            elif action == 'volume_up':
                sys_ctrl.volume_up(int(params.get('amount', 10)))

            elif action == 'volume_down':
                sys_ctrl.volume_down(int(params.get('amount', 10)))

            elif action == 'volume_mute':
                sys_ctrl.mute()

            elif action == 'volume_unmute':
                sys_ctrl.unmute()

            elif action == 'set_volume':
                sys_ctrl.set_volume(int(params.get('level', 50)))

            # ── Power ─────────────────────────────────────────────────────────
            elif action == 'shutdown':
                sys_ctrl.shutdown()

            elif action == 'restart':
                sys_ctrl.restart()

            elif action == 'sleep':
                sys_ctrl.sleep()

            elif action == 'lock':
                sys_ctrl.lock_screen()

            # ── Files ─────────────────────────────────────────────────────────
            elif action == 'take_screenshot':
                fp = screenshot_mod.take_screenshot()
                if fp:
                    self.window.add_system_message(f"Screenshot saved → {os.path.basename(fp)}")

            elif action == 'open_folder':
                file_ctrl.open_folder(params.get('path', 'desktop'))

            # ── Timers ────────────────────────────────────────────────────────
            elif action == 'set_timer':
                seconds = int(params.get('seconds', 60))
                label   = params.get('label', 'Timer')

                def _done(lbl):
                    msg = f"Hey, your {lbl} is done!"
                    self.voice_output.speak(msg)
                    self.window.add_aria_message(msg)

                self.timer_manager.set_timer(seconds, label, on_complete=_done)

            # ── Clipboard / Typing ────────────────────────────────────────────
            elif action == 'type_text':
                clip_ctrl.type_text(params.get('text', ''))

            elif action == 'copy_text':
                clip_ctrl.copy_to_clipboard(params.get('text', ''))

            # ── Pass-through ──────────────────────────────────────────────────
            elif action in ('none', 'get_weather'):
                pass  # Conversation or already handled above

            else:
                print(f"[ARIA] Unrecognised action: '{action}' — treating as conversation.")

        except Exception as e:
            print(f"[ARIA] Action error ({action}): {e}")
            import traceback; traceback.print_exc()
            self.window.add_system_message(f"Action error: {e}")

    # ── Settings ──────────────────────────────────────────────────────────────

    def _on_settings_saved(self, new_config: dict):
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
        self.voice_output.set_voice(self.config.get('voice_name', 'en-GB-RyanNeural'))
        self.voice_output.set_speed(self.config.get('voice_speed', 175))
        print("[ARIA] Settings updated.")

    def _reset_memory(self):
        self.ai_brain.reset_memory()

    # ── Run ───────────────────────────────────────────────────────────────────

    def run(self):
        threading.Thread(target=self._startup_tasks, daemon=True, name="ARIA-Startup").start()
        self.window.run()
        self.hotkey.stop()
        self.voice_output.stop()
        print("[ARIA] Shutting down.")


def main():
    print("=" * 55)
    print("  A.R.I.A. — Adaptive Real-time Intelligent Assistant")
    print("=" * 55)
    try:
        aria = ARIAAssistant()
        aria.run()
    except KeyboardInterrupt:
        print("\n[ARIA] Interrupted.")
        sys.exit(0)
    except Exception as e:
        print(f"[ARIA] Fatal error: {e}")
        import traceback; traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
