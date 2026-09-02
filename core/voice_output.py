"""
ARIA Neural Voice Output Module
Uses Microsoft Edge Neural TTS for ultra-realistic, expressive, human-like voice output
with natural emotions, pitch inflections, and conversational cadence.
Falls back to pyttsx3 offline if network is unavailable.
"""

import os
import tempfile
import threading
import queue
import asyncio
import time

# Suppress Pygame welcome banner
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
import pygame

try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False

try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False


class VoiceOutput:
    """
    High-fidelity Neural Text-to-Speech Engine for ARIA.
    Provides human-level vocal emotion and natural inflection.
    """

    def __init__(
        self,
        voice: str = "en-US-GuyNeural",
        speed: int = 175,
        volume: float = 0.95
    ):
        self.voice = voice
        self.volume = volume
        self._speed = speed
        self._speaking = False
        self._on_start = None
        self._on_finish = None

        # Initialize Pygame mixer for crisp audio playback
        try:
            pygame.mixer.init()
        except Exception as e:
            print(f"[VoiceOutput] Pygame mixer init warning: {e}")

        # Dedicated background audio worker thread
        self._queue: queue.Queue = queue.Queue()
        self._thread = threading.Thread(target=self._worker, daemon=True, name="ARIA-NeuralTTS")
        self._thread.start()

    def _worker(self):
        """Worker thread that processes and speaks queued text utterances."""
        while True:
            item = self._queue.get()
            if item is None:
                break

            text = item.strip()
            if not text:
                self._queue.task_done()
                continue

            self._speaking = True
            if self._on_start:
                try:
                    self._on_start()
                except Exception:
                    pass

            # 1. Attempt High-Fidelity Neural Speech
            success = False
            if EDGE_TTS_AVAILABLE:
                success = self._speak_neural(text)

            # 2. Offline Fallback if Neural TTS fails or offline
            if not success and PYTTSX3_AVAILABLE:
                self._speak_offline(text)

            self._speaking = False
            if self._on_finish:
                try:
                    self._on_finish()
                except Exception:
                    pass

            self._queue.task_done()

    def _speak_neural(self, text: str) -> bool:
        """Generate and play audio using Microsoft Neural TTS (Human-level emotion)."""
        temp_file = None
        try:
            # Create a unique temporary file
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
                temp_path = f.name
            temp_file = temp_path

            # Calculate rate adjustment from speed setting (175 is default ~ 0%)
            rate_delta = int((self._speed - 175) / 2)
            rate_str = f"+{rate_delta}%" if rate_delta >= 0 else f"{rate_delta}%"

            async def _generate():
                communicate = edge_tts.Communicate(
                    text=text,
                    voice=self.voice,
                    rate=rate_str,
                    volume="+0%"
                )
                await communicate.save(temp_path)

            # Run asynchronous edge-tts generation in local event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(_generate())
            loop.close()

            # Play generated neural audio via pygame mixer
            pygame.mixer.music.load(temp_path)
            pygame.mixer.music.set_volume(self.volume)
            pygame.mixer.music.play()

            while pygame.mixer.music.get_busy():
                time.sleep(0.04)

            pygame.mixer.music.unload()
            return True

        except Exception as e:
            print(f"[VoiceOutput] Neural TTS note: {e} — falling back to system engine.")
            return False

        finally:
            if temp_file and os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception:
                    pass

    def _speak_offline(self, text: str):
        """Offline fallback using Windows SAPI5."""
        try:
            engine = pyttsx3.init()
            engine.setProperty('rate', self._speed)
            engine.setProperty('volume', self.volume)
            voices = engine.getProperty('voices')
            for v in voices:
                if 'david' in v.name.lower() or 'male' in v.name.lower():
                    engine.setProperty('voice', v.id)
                    break
            engine.say(text)
            engine.runAndWait()
        except Exception as e:
            print(f"[VoiceOutput] Offline TTS error: {e}")

    # ── Public API ──────────────────────────────────────────────────────────

    def speak(self, text: str):
        """Queue text for natural vocalization (non-blocking)."""
        if text and text.strip():
            self._queue.put(text.strip())

    def is_speaking(self) -> bool:
        return self._speaking

    def set_callbacks(self, on_start=None, on_finish=None):
        """Register callbacks for speech start and completion events."""
        self._on_start = on_start
        self._on_finish = on_finish

    def set_voice(self, voice_name: str):
        self.voice = voice_name

    def set_speed(self, speed: int):
        self._speed = speed

    def set_volume(self, volume: float):
        self.volume = volume

    def stop(self):
        """Terminate the TTS background worker."""
        self._queue.put(None)
        try:
            pygame.mixer.quit()
        except Exception:
            pass
