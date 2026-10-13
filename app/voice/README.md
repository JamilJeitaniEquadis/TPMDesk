# Voice summary

Transcribes whatever your laptop plays (speakers, headphones, Bluetooth: a call, a video, a
training...) and summarises it with Claude. The text appears live while you listen.
Whisper runs on your laptop, so the audio never leaves it; only the text goes to Claude.

## Start

Double-click **Voice summary.bat**. The first time it sets everything up by itself:

1. installs Python 3.12 for your account if it is missing (with winget);
2. installs the voice packages (a few minutes);
3. asks for your Anthropic API key and saves it (Enter skips it: you then only get the transcript).

If Python can't be installed automatically (blocked by IT), install it from python.org or the
Company Portal, tick "Add python.exe to PATH", and double-click the file again.

## Each time

Double-click **Voice summary.bat**, or from this folder:

    python voice_summary.py --title "Supplier call" --lang fr

Play what you want to hear. Press **Enter** in the window when you are done. You get
`recordings/<date>_<title>/transcript.txt` and `summary.md` (overview, key points, action items,
open questions). Drop `transcript.txt` in the desk's Voice summary tab to summarise it there instead.

- It follows the device you are listening on: plug in headphones mid-way and it keeps going.
- `--mic` also records your microphone (use it when you speak too, e.g. in a call).
- `--model medium` transcribes better (accents, French) but slower; `tiny` is the fastest.
  The first run downloads the model.
- `--from recordings/<folder>` summarises a transcript again; `--no-summary` skips Claude.
- Windows and Linux capture the laptop sound directly. On a Mac, install BlackHole first.

If what you capture includes other people (a call), tell them it is being transcribed.

Tests: `python -m pytest app/voice` from the repository root.
