"""
ARIA Voice Input Module — Whisper-Powered Local Speech Recognition
Uses OpenAI Whisper (offline, runs 100% on your PC) for highly accurate transcription.
Falls back to Google STT if Whisper is unavailable.
"""

import speech_recognition as sr
import numpy as np
import threading
import time

# Try to import Whisper
try:
    import whisper
    import sounddevice as sd
    import scipy.io.wavfile as wav_io
    import tempfile, os
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False

_whisper_model = None
_whisper_lock = threading.Lock()


def _load_whisper_model(size="base"):
    """Load Whisper model once and cache it."""
    global _whisper_model
    with _whisper_lock:
        if _whisper_model is None:
            print(f"[VoiceInput] Loading Whisper '{size}' model (first run only)...")
            _whisper_model = whisper.load_model(size)
            print("[VoiceInput] Whisper model ready.")
    return _whisper_model


class VoiceInput:
    """
    High-accuracy Speech-to-Text using OpenAI Whisper (local, offline).
    Falls back to Google Web Speech if Whisper is not installed.
    """

    def __init__(self, language: str = "en", device_index: int = None):
        self.language = language
        self.device_index = device_index
        self.recognizer = sr.Recognizer()

        # Acoustic settings
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.8
        self.recognizer.phrase_threshold = 0.1
        self.recognizer.non_speaking_duration = 0.4

        # Load Whisper in background thread so startup is fast
        if WHISPER_AVAILABLE:
            threading.Thread(target=_load_whisper_model, args=("base",), daemon=True).start()
        else:
            print("[VoiceInput] Whisper not found. Using Google STT fallback.")

    def calibrate(self, duration: float = 1.0):
        """Calibrate microphone against background room noise."""
        try:
            with sr.Microphone(device_index=self.device_index) as source:
                print("[VoiceInput] Calibrating microphone...")
                self.recognizer.adjust_for_ambient_noise(source, duration=duration)
                print(f"[VoiceInput] Ambient baseline: {self.recognizer.energy_threshold:.1f}")
        except Exception as e:
            print(f"[VoiceInput] Calibration notice: {e}")

    def listen(self, timeout: float = 8, phrase_time_limit: float = 15) -> str | None:
        """Listen for a voice command and return transcribed text."""
        try:
            with sr.Microphone(device_index=self.device_index) as source:
                print("[VoiceInput] Listening...")
                audio = self.recognizer.listen(
                    source,
                    timeout=timeout,
                    phrase_time_limit=phrase_time_limit
                )

            # Try Whisper first (local, most accurate)
            if WHISPER_AVAILABLE:
                result = self._transcribe_whisper(audio)
                if result:
                    print(f"[VoiceInput][Whisper] Heard: '{result}'")
                    return result

            # Fallback: Google STT
            return self._transcribe_google(audio)

        except sr.WaitTimeoutError:
            print("[VoiceInput] No speech detected within timeout.")
            return None
        except Exception as e:
            print(f"[VoiceInput] Capture error: {e}")
            return None

    def _transcribe_whisper(self, audio: sr.AudioData) -> str | None:
        """Transcribe audio using local Whisper model."""
        try:
            model = _load_whisper_model()
            # Convert AudioData to numpy array
            raw = np.frombuffer(audio.get_raw_data(convert_rate=16000, convert_width=2), dtype=np.int16)
            arr = raw.astype(np.float32) / 32768.0

            result = model.transcribe(arr, language="en", fp16=False, task="transcribe")
            text = result.get("text", "").strip()
            # Filter out empty or noise-only outputs
            noise_patterns = [".", "..", "...", "thank you", "thanks", "you"]
            if text and text.lower() not in noise_patterns and len(text) > 1:
                return text
            return None
        except Exception as e:
            print(f"[VoiceInput] Whisper error: {e}")
            return None

    def _transcribe_google(self, audio: sr.AudioData) -> str | None:
        """Fallback to Google Web Speech API."""
        for lang in [self.language, "en-US", "en-IN"]:
            try:
                text = self.recognizer.recognize_google(audio, language=lang)
                if text and text.strip():
                    print(f"[VoiceInput][Google/{lang}] Heard: '{text.strip()}'")
                    return text.strip()
            except sr.UnknownValueError:
                continue
            except sr.RequestError as e:
                print(f"[VoiceInput] Google STT error: {e}")
                break
        return None

    def set_language(self, lang: str):
        """Update recognition language."""
        if lang:
            self.language = lang

    def set_device_index(self, idx: int):
        """Set specific microphone device index."""
        self.device_index = idx

    @staticmethod
    def list_microphones() -> list[str]:
        """List all available microphone devices."""
        try:
            return sr.Microphone.list_microphone_names()
        except Exception as e:
            print(f"[VoiceInput] Could not enumerate microphones: {e}")
            return []
