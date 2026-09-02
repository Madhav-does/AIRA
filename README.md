# 🤖 ARIA — Tony Stark JARVIS AI Voice Assistant

**ARIA** (Adaptive Real-time Intelligent Assistant) is a high-performance, voice-controlled AI desktop assistant for Windows, modeled after **Tony Stark's JARVIS**. Powered by **Google Gemini 2.0 Flash** and **Microsoft Neural Speech**, ARIA listens to your natural voice commands, talks back like an intelligent and warm best friend, and controls your PC in real-time.

---

## ✨ Key Features

| Feature | Description |
|---|---|
| ⚡ **JARVIS Arc Reactor HUD** | Centered 96-bar circular frequency visualizer that pulses and dances to voice & speech frequencies in real-time. |
| 🖥️ **Responsive Fullscreen** | Fullscreen-adaptive console (**F11**) with zero empty black gaps and dynamic telemetry scaling. |
| 🎙️ **Ultra-Realistic Male Voice** | Powered by Microsoft's Neural Voice Engine (`en-US-GuyNeural`, `en-GB-RyanNeural`, `en-US-ChristopherNeural`) with natural emotion and inflection. |
| 🧠 **Gemini 2.0 Flash AI Brain** | Multi-turn conversational memory, witty banter, and deep intelligence tuned like a trusted companion. |
| ⌨️ **System-Wide Global Hotkeys** | `Ctrl + Space` to summon/toggle ARIA from anywhere; `P` (or `F2`) for direct voice activation. |
| 🗣️ **Dual-Pass Speech Recognition** | High-accuracy Google STT with dual-pass accent matching (`en-IN` Indian English & `en-US` American English). |
| 📊 **Live Hardware Diagnostics** | Real-time animated **CPU %** and **RAM %** meters updating live. |
| 🖥️ **Full PC & Application Control** | Open applications, search YouTube/Google, control volume, set multi-timers, get weather, take screenshots, lock/sleep PC. |
| ⚙️ **Practical Settings Console** | Configure Operator identity, API keys, voice profiles with live audio preview buttons, and hotkeys. |

---

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/Madhav-does/ARIA-Assistant.git
cd ARIA-Assistant
```

### 2. Install Dependencies
Double-click **`setup.bat`** or manually install:
```bash
pip install -r requirements.txt
```

### 3. Get Your Free Gemini API Key
1. Visit [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
2. Sign in with your Google account and click **"Create API Key"**
3. Copy the key.

### 4. Launch ARIA
Double-click **`start_aria.bat`** or run:
```bash
python main.py
```
Open **Settings (⚙)** inside ARIA, paste your API key, and click **Save & Synchronize**.

---

## ⌨️ Global Shortcuts

| Shortcut | Function |
|---|---|
| **`Ctrl + Space`** | **Summon / Toggle ARIA** (brings window to front or hides to background) |
| **`P`** *(or `F2`)* | **Direct Voice Activation** (un-minimizes ARIA & starts listening immediately) |
| **`F11`** | **Toggle Fullscreen Mode** |
| **`Esc`** | **Exit Fullscreen Mode** |

---

## 💬 Example Voice Commands

### Applications & Web
- *"Open Chrome"* / *"Open VS Code"* / *"Open Spotify"*
- *"Search cats on YouTube"* / *"Search Python tutorials on Google"*
- *"Open GitHub"* / *"Open Downloads folder"*

### System Controls
- *"Turn volume up by 20"* / *"Set volume to 60 percent"* / *"Mute audio"*
- *"Take a screenshot"* *(saved to Desktop)*
- *"Lock my screen"* / *"Put PC to sleep"*

### Weather & Timers
- *"What's the weather in Delhi?"*
- *"Set a timer for 5 minutes called pizza"*

### Natural Conversation
- *"Hey ARIA, how are you doing today?"*
- *"Tell me a funny joke"*
- *"Who is Tony Stark?"*
- *"Explain quantum computing in simple terms"*

---

## 📁 Project Architecture

```
ARIA-Assistant/
├── main.py                  # Main orchestrator & lifecycle manager
├── config.py                # Configuration loader & defaults
├── requirements.txt         # Package dependencies
├── setup.bat                # Automated Windows setup script
├── start_aria.bat           # One-click launcher
├── verify.py                # Diagnostic test runner
│
├── core/
│   ├── voice_input.py       # Dual-pass SpeechRecognition (PyAudio + Google STT)
│   ├── voice_output.py      # Microsoft Neural TTS (edge-tts + pygame audio)
│   ├── ai_brain.py          # Gemini 2.0 Flash conversational brain
│   └── hotkey_handler.py    # Global Windows keyboard hooks
│
├── actions/
│   ├── app_control.py       # Application launch & control
│   ├── system_control.py    # Audio volume & power management
│   ├── web_control.py       # Web browser & search queries
│   ├── file_control.py      # File explorer navigation
│   ├── timer_control.py     # Multi-threaded countdown timers
│   ├── weather.py           # Live weather data (wttr.in)
│   └── screenshot.py        # Desktop screen capture
│
└── ui/
    └── app_window.py        # Responsive fullscreen JARVIS Arc Reactor HUD
```

---

## 🔒 Security & Privacy

- All configuration settings and API keys are stored locally in `aria_config.json` (gitignored).
- All PC actions and audio processing run strictly on your local machine.
- Speech audio is sent securely to your own personal Google Gemini API endpoint.

---

*Built with ❤️ for Madhav.*
