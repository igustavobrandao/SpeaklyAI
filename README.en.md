# Whisper Microfone

![Status](https://img.shields.io/badge/status-Alpha%200.2.0-orange) ![Python](https://img.shields.io/badge/python-3.11%2B-blue) ![License](https://img.shields.io/badge/license-MIT-green) ![Platform](https://img.shields.io/badge/platform-Windows-blue)

An open source replacement for Windows' built-in Win+H dictation. Press a hotkey, speak, release — the transcribed text appears wherever your cursor is. Transcription powered by [Groq Whisper API](https://console.groq.com/), no local model, no GPU required.

---

## Features

- **Global push-to-talk** — configurable hotkey (default: `Ctrl+Alt+Space`) works in any window
- **Groq-powered transcription** — uses Groq's Whisper API; fast, no GPU, no local model needed
- **Mini dictation popup** — floating dark card window activated by `Ctrl+F9`; shows recording state and countdown
- **Integrated VAD** — Silero VAD strips silence before sending, reducing hallucinations and API cost
- **Smart text injection** — pastes transcribed text directly into the active window via clipboard
- **Dark Apple-style interface** — 4 tabs: Home, Config, History, About
- **Multilingual** — UI in PT-BR and EN; transcription supports any language Whisper handles
- **Zero hardcoded values** — everything configurable via TOML files
- **Transcription history** — stored locally in SQLite, searchable from the interface
- **System tray** — runs in the background without occupying the taskbar

---

## Requirements

| Component | Minimum version |
|---|---|
| Windows | 10 / 11 (64-bit) |
| Python | 3.11 or higher |
| Groq API Key | Free at [console.groq.com](https://console.groq.com/) |

> No GPU required. All transcription is done in the cloud via Groq.

---

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/Gustavo1341/whisper-microphone.git
cd whisper-microphone

# 2. Create and activate the virtual environment
python -m venv .venv
.venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create the configuration file with your Groq key
echo GROQ_API_KEY=your_key_here > .env
```

Get your free key at [console.groq.com/keys](https://console.groq.com/keys).

---

## Starting the app

```bash
cd whisper-microphone
.venv\Scripts\activate
python -m whisper_microfone
```

The app minimizes to the system tray. The main window can be opened by clicking the tray icon.

---

## How to use

### Push-to-talk (`Ctrl+Alt+Space`)

1. Place your cursor in any text field (editor, browser, chat, etc.)
2. Hold `Ctrl+Alt+Space`
3. Speak
4. Release — the transcribed text is automatically pasted where your cursor was

### Mini popup (`Ctrl+F9`)

Use when you don't have an active text field or want to see the recording status:

1. Press `Ctrl+F9` — opens the floating popup with a 1-second countdown
2. Speak after the countdown
3. Press `Ctrl+F9` again — stops recording and transcribes
4. The transcribed text is available in the clipboard to paste anywhere (`Ctrl+V`)

> **Note for laptop keyboards:** Some keyboards internally report `Ctrl+F9` as a special key code. If the shortcut doesn't work, see the Troubleshooting section below.

---

## Default shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl+Alt+Space` | Push-to-talk (hold to record, release to transcribe) |
| `Ctrl+F9` | Open/close mini dictation popup |
| `Ctrl+Alt+P` | Pause / resume the hotkey listener |
| `Ctrl+Alt+W` | Show / hide the main window |

All shortcuts are configurable in `%APPDATA%\whisper-microfone\config\shortcuts.toml`.

---

## Configuration

Configuration files are stored in `%APPDATA%\whisper-microfone\config\` and created automatically on first launch.

| File | Contents |
|---|---|
| `config.toml` | App, model, audio, VAD, transcription, injection, UI, history, logs |
| `shortcuts.toml` | Keyboard shortcuts |
| `theme.toml` | Colors, fonts, and layout |
| `advanced.toml` | Advanced settings |

---

## Troubleshooting

**Popup does not open with `Ctrl+F9`**

Some laptop keyboards (especially those with Fn keys) report `Ctrl+F9` as `F17` to the operating system. If that's the case, edit `%APPDATA%\whisper-microfone\config\shortcuts.toml` and change the combination:

```toml
[open_mic_popup]
combination = "f17"
enabled = true
```

To find out which code your key generates, run:
```bash
.venv\Scripts\python.exe -c "
from pynput.keyboard import Listener
def show(k): print(k)
with Listener(on_press=show) as l: l.join()
"
```

**Microphone not detected**

Check available devices:
```bash
python -c "import sounddevice; print(sounddevice.query_devices())"
```
Configure the microphone in `config.toml → [audio] → device_name` or `device_index`.

**Text is not pasted into the active window**

The app uses the clipboard to inject text. Make sure the target window is focused when the transcription finishes. If the target window runs with elevated privileges (e.g., Task Manager), start the app as Administrator as well.

**API Key error**

Make sure the `.env` file at the project root contains `GROQ_API_KEY=your_key`. Get a free key at [console.groq.com/keys](https://console.groq.com/keys).

---

## License

MIT — see the [LICENSE](LICENSE) file for details.

Author: Gustavo Brandão
