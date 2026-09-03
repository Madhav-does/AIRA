#!/usr/bin/env python3
"""
ARIA — Adaptive Real-time Intelligent Assistant
Main orchestrator: wires voice I/O, AI brain, MCP client, PC actions, hotkeys, UI.
"""

import sys
import os
import threading
import time

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import config as cfg
from core.voice_input    import VoiceInput
from core.voice_output   import VoiceOutput
from core.ai_brain       import AIBrain
from core.hotkey_handler import HotkeyHandler
from core.mcp_client     import MCPManager
from ui.app_window       import AppWindow

import actions.timer_control as tc


class ARIAAssistant:
    """Top-level orchestrator."""

    def __init__(self):
        self.config = cfg.load_config()

        # ── MCP Client (connects to all servers) ─────────────────────────────
        extra_servers = self.config.get('mcp_servers', [])
        self.mcp_manager = MCPManager(extra_servers=extra_servers)

        # ── Core components ──────────────────────────────────────────────────
        self.voice_input = VoiceInput(
            language=self.config.get('stt_language', 'en-IN')
        )
        self.voice_output = VoiceOutput(
            voice=self.config.get('voice_name', 'en-GB-RyanNeural'),
            speed=self.config.get('voice_speed', 175),
            volume=self.config.get('voice_volume', 0.9),
        )
        self.ai_brain = AIBrain(
            api_key=self.config.get('gemini_api_key', ''),
            user_name=self.config.get('user_name', 'Madhav'),
            mcp_manager=self.mcp_manager,
        )
        self.timer_manager = tc.TimerManager()

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
        user = self.config.get('user_name', 'Madhav')

        self.window.add_system_message("Calibrating acoustic sensors...")
        self.voice_input.calibrate()
        self.window.add_system_message("Sensors nominal.")

        # Connect MCP servers
        self.window.add_system_message("Connecting MCP tool servers...")
        self.mcp_manager.start()
        n_tools = len(self.mcp_manager.get_tool_schemas())
        self.window.add_system_message(
            f"MCP online — {n_tools} external tools available."
        )

        # Reinitialize AI brain now that MCP is ready (picks up MCP tools)
        self.ai_brain.configure(
            api_key=self.config.get('gemini_api_key', ''),
            user_name=user,
            mcp_manager=self.mcp_manager,
        )

        self.hotkey.start()

        if not self.config.get('gemini_api_key'):
            msg = (f"Hey {user}! I'm ARIA, online and ready. "
                   f"Just add your Gemini API key in Settings and we're good to go!")
            self.window.add_system_message("⚠ No API key — open ⚙ Settings.")
        else:
            hk = self.config.get('hotkey', 'P').upper()
            msg = (f"Hey {user}! ARIA online, all systems nominal — "
                   f"{n_tools} MCP tools loaded. "
                   f"Press {hk} and tell me what you need!")

        self.window.add_aria_message(msg)
        self.voice_output.speak(msg)

    # ── Main Voice Loop ───────────────────────────────────────────────────────

    def _start_listening(self):
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
        """Full pipeline: listen → AI (with tool loop) → speak."""

        # 1. LISTEN
        self.window.set_status('listening')
        text = self.voice_input.listen(timeout=8, phrase_time_limit=15)

        if not text:
            user = self.config.get('user_name', 'Madhav')
            self.window.set_status('idle')
            self.window.add_system_message("No audio captured.")
            self.voice_output.speak(
                f"I didn't catch that, {user}. Try speaking a bit louder?"
            )
            return

        self.window.add_user_message(text)
        print(f"[ARIA] Heard: '{text}'")

        # 2. THINK + TOOL LOOP (handled inside ai_brain now)
        self.window.set_status('thinking')
        speech, actions_taken = self.ai_brain.process(text)

        # 3. Handle any special actions returned by tools
        for act in actions_taken:
            self._handle_special_result(act)
            # Log each tool call in the UI
            self.window.add_system_message(
                f"⚙ {act['tool']}({_fmt_args(act['args'])}) → {str(act['result'])[:60]}"
            )

        # 4. SPEAK
        self.window.add_aria_message(speech)
        self.voice_output.speak(speech)

    def _handle_special_result(self, act: dict):
        """Handle special sentinel results from tools that need main.py orchestration."""
        result = str(act.get('result', ''))
        if result.startswith('__SET_TIMER__:'):
            # Format: __SET_TIMER__:seconds:label
            parts = result.split(':', 2)
            try:
                seconds = int(parts[1])
                label   = parts[2] if len(parts) > 2 else 'Timer'
                def _done(lbl):
                    msg = f"Hey, your {lbl} is done!"
                    self.voice_output.speak(msg)
                    self.window.add_aria_message(msg)
                self.timer_manager.set_timer(seconds, label, on_complete=_done)
                print(f"[ARIA] Timer set: {seconds}s — '{label}'")
            except Exception as e:
                print(f"[ARIA] Timer parse error: {e}")

    # ── Settings ──────────────────────────────────────────────────────────────

    def _on_settings_saved(self, new_config: dict):
        self.config.update(new_config)
        cfg.save_config(self.config)

        self.ai_brain.configure(
            api_key=self.config.get('gemini_api_key', ''),
            user_name=self.config.get('user_name', 'Madhav'),
            mcp_manager=self.mcp_manager,
        )
        self.hotkey.update_hotkeys(
            new_talk_hotkey=self.config.get('hotkey', 'P'),
            new_summon_hotkey=self.config.get('summon_hotkey', 'ctrl+space'),
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
        self.mcp_manager.stop()
        print("[ARIA] Shutdown complete.")


def _fmt_args(args: dict) -> str:
    """Format tool args for display."""
    if not args:
        return ""
    parts = [f"{k}={repr(v)[:20]}" for k, v in list(args.items())[:2]]
    return ", ".join(parts)


def main():
    print("=" * 55)
    print("  A.R.I.A. — Adaptive Real-time Intelligent Assistant")
    print("  With MCP Client Integration")
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
