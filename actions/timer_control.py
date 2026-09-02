"""
ARIA Timer Manager
Manages countdown timers that fire a callback when they expire.
"""

import threading
import time
from datetime import datetime, timedelta
from typing import Callable


class TimerManager:
    """Thread-safe manager for multiple simultaneous countdown timers."""

    def __init__(self):
        self._timers: list[dict] = []
        self._lock = threading.Lock()

    def set_timer(
        self,
        seconds: int,
        label: str = 'Timer',
        on_complete: Callable[[str], None] = None
    ) -> datetime:
        """
        Start a countdown timer.

        Args:
            seconds:     Duration of the timer in seconds.
            label:       Friendly name for the timer.
            on_complete: Callback called with label when timer fires.

        Returns:
            The datetime when the timer will fire.
        """
        end_time = datetime.now() + timedelta(seconds=seconds)

        timer_info = {
            'label': label,
            'seconds': seconds,
            'end_time': end_time,
        }

        with self._lock:
            self._timers.append(timer_info)

        # Start background countdown thread
        thread = threading.Thread(
            target=self._countdown,
            args=(seconds, label, on_complete, timer_info),
            daemon=True,
            name=f"ARIA-Timer-{label}"
        )
        thread.start()

        print(f"[Timer] Set '{label}' for {seconds}s (ends at {end_time.strftime('%H:%M:%S')})")
        return end_time

    def _countdown(self, seconds: int, label: str, on_complete, timer_info: dict):
        """Worker that sleeps then fires the callback."""
        time.sleep(seconds)
        print(f"[Timer] '{label}' completed!")

        # Remove from active list
        with self._lock:
            if timer_info in self._timers:
                self._timers.remove(timer_info)

        if on_complete:
            on_complete(label)

    def get_active_timers(self) -> list[dict]:
        """Return list of timers that haven't fired yet."""
        now = datetime.now()
        with self._lock:
            return [t for t in self._timers if t['end_time'] > now]
