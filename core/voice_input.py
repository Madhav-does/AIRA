"""
ARIA Voice Input Module
Handles high-accuracy microphone capture and speech-to-text conversion via Google Web Speech API.
Features dual-pass accent recognition (Indian English / US English), dynamic noise gating,
and microphone device selection.
"""

import speech_recognition as sr


class VoiceInput:
    """
    Robust Speech-to-Text handler with dual-pass accent matching and acoustic noise adaptation.
    """

    def __init__(self, language: str = "en-IN", device_index: int = None):
        self.language = language
        self.device_index = device_index
        self.recognizer = sr.Recognizer()

        # Acoustic Sensitivity & Timing Configurations
        self.recognizer.energy_threshold = 250
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.dynamic_energy_adjustment_damping = 0.15
        self.recognizer.dynamic_energy_ratio = 1.5
        self.recognizer.pause_threshold = 1.0       # 1.0s silence to conclude utterance (avoids premature cutoff)
        self.recognizer.phrase_threshold = 0.2     # Minimum audio length to consider speech
        self.recognizer.non_speaking_duration = 0.5

    def calibrate(self, duration: float = 1.2):
        """
        Calibrate microphone against background room noise.
        """
        try:
            with sr.Microphone(device_index=self.device_index) as source:
                print("[VoiceInput] Calibrating microphone for ambient room noise...")
                self.recognizer.adjust_for_ambient_noise(source, duration=duration)
                print(f"[VoiceInput] Ambient baseline energy threshold: {self.recognizer.energy_threshold:.1f}")
        except Exception as e:
            print(f"[VoiceInput] Calibration notice: {e}")

    def listen(self, timeout: float = 7, phrase_time_limit: float = 15) -> str | None:
        """
        Listen for a user voice command and transcribe into text.

        Returns:
            Transcribed text string, or None if no clear speech was captured.
        """
        try:
            with sr.Microphone(device_index=self.device_index) as source:
                print(f"[VoiceInput] Microphone active ({self.language}). Listening...")
                audio = self.recognizer.listen(
                    source,
                    timeout=timeout,
                    phrase_time_limit=phrase_time_limit
                )

            # 1. Primary Pass (Configured Language, e.g. en-IN or en-US)
            try:
                text = self.recognizer.recognize_google(audio, language=self.language)
                if text and text.strip():
                    print(f"[VoiceInput] Heard (Primary {self.language}): '{text.strip()}'")
                    return text.strip()
            except sr.UnknownValueError:
                pass
            except sr.RequestError as e:
                print(f"[VoiceInput] Primary STT request error: {e}")

            # 2. Secondary Pass (Fallback Accent / Language e.g. en-US if primary is en-IN)
            fallback_lang = "en-US" if self.language == "en-IN" else "en-IN"
            try:
                text = self.recognizer.recognize_google(audio, language=fallback_lang)
                if text and text.strip():
                    print(f"[VoiceInput] Heard (Fallback {fallback_lang}): '{text.strip()}'")
                    return text.strip()
            except sr.UnknownValueError:
                print("[VoiceInput] Audio captured but could not resolve clear words.")
                return None
            except sr.RequestError as e:
                print(f"[VoiceInput] Fallback STT request error: {e}")
                return None

        except sr.WaitTimeoutError:
            print("[VoiceInput] No vocal activity detected within timeout period.")
            return None
        except Exception as e:
            print(f"[VoiceInput] Acoustic capture error: {e}")
            return None

    def set_language(self, lang: str):
        """Update speech recognition language (e.g. 'en-IN', 'en-US', 'en-GB')."""
        if lang:
            self.language = lang

    def set_device_index(self, idx: int):
        """Set specific microphone device index."""
        self.device_index = idx

    @staticmethod
    def list_microphones() -> list[str]:
        """List all available system microphone devices."""
        try:
            return sr.Microphone.list_microphone_names()
        except Exception as e:
            print(f"[VoiceInput] Could not enumerate microphones: {e}")
            return []
