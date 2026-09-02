"""
ARIA Hotkey Handler
Manages global system-wide keyboard shortcuts for:
1. Voice Activation (brings ARIA to front & begins listening)
2. Window Summon / Toggle (shows/hides ARIA console from anywhere)
"""

import keyboard
import threading


class HotkeyHandler:
    """
    Registers global Windows hotkeys to summon ARIA and trigger voice interaction.
    """

    def __init__(
        self,
        talk_hotkey: str = 'P',
        summon_hotkey: str = 'ctrl+space',
        on_talk=None,
        on_summon=None
    ):
        self.talk_hotkey = talk_hotkey.strip().lower() if talk_hotkey else 'p'
        self.summon_hotkey = summon_hotkey.strip().lower() if summon_hotkey else 'ctrl+space'
        self.on_talk = on_talk
        self.on_summon = on_summon
        self._running = False
        self._registered_keys = []

    def start(self):
        """Register configured hotkeys with Windows keyboard hook."""
        self._running = True
        self._register_all()

    def _register_all(self):
        self._unregister_all()

        # 1. Voice Activation Hotkey
        if self.talk_hotkey and self.on_talk:
            try:
                keyboard.add_hotkey(self.talk_hotkey, self._handle_talk)
                self._registered_keys.append(self.talk_hotkey)
                print(f"[Hotkey] Voice trigger registered: '{self.talk_hotkey.upper()}'")
            except Exception as e:
                print(f"[Hotkey] Could not register voice hotkey '{self.talk_hotkey}': {e}")

        # 2. Window Summon / Toggle Hotkey (if different from talk hotkey)
        if self.summon_hotkey and self.on_summon and self.summon_hotkey != self.talk_hotkey:
            try:
                keyboard.add_hotkey(self.summon_hotkey, self._handle_summon)
                self._registered_keys.append(self.summon_hotkey)
                print(f"[Hotkey] Window summon registered: '{self.summon_hotkey.upper()}'")
            except Exception as e:
                print(f"[Hotkey] Could not register summon hotkey '{self.summon_hotkey}': {e}")

    def _handle_talk(self):
        """Dispatched when voice hotkey is pressed."""
        if self.on_talk and self._running:
            threading.Thread(target=self.on_talk, daemon=True, name="ARIA-TalkTrigger").start()

    def _handle_summon(self):
        """Dispatched when window toggle hotkey is pressed."""
        if self.on_summon and self._running:
            threading.Thread(target=self.on_summon, daemon=True, name="ARIA-SummonTrigger").start()

    def _unregister_all(self):
        for k in self._registered_keys:
            try:
                keyboard.remove_hotkey(k)
            except Exception:
                pass
        self._registered_keys.clear()

    def stop(self):
        """Unregister all hotkeys."""
        self._running = False
        self._unregister_all()

    def update_hotkeys(self, new_talk_hotkey: str = None, new_summon_hotkey: str = None):
        """Update hotkey shortcuts at runtime."""
        if new_talk_hotkey:
            self.talk_hotkey = new_talk_hotkey.strip().lower()
        if new_summon_hotkey:
            self.summon_hotkey = new_summon_hotkey.strip().lower()
        if self._running:
            self._register_all()
