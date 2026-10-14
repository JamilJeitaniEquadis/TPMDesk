# Voice summary

Transcribes whatever your laptop plays (speakers, headphones, Bluetooth: a call, a video, a
training...) and summarises it with Claude. The text appears live while you listen.
Whisper runs on your laptop, so the audio never leaves it; only the text goes to Claude.

## Start

Double-click **Voice summary.bat**. The first time it sets everything up by itself:

1. installs Python 3.12 silently for your account only if it is missing (python.org installer, no admin rights needed);
2. installs the voice packages (a few minutes);

If Python can't be installed automatically (blocked by IT), install it from python.org or the
Company Portal, tick "Add python.exe to PATH", and double-click the file again.

## Summaries with your Claude account (one time)

The summary is written by **Claude Code**, signed in with your Claude account: no API key.

1. Install it with Anthropic's official installer: open **PowerShell** and run
   `irm https://claude.ai/install.ps1 | iex` (for your account only, no admin).
   Instructions: https://code.claude.com/docs/en/setup
2. Sign in once: open a new terminal, type `claude`, log in with your Claude account, then type `/exit`.

Without Claude Code, the script copies the transcript and opens the desk on claude.ai instead:
paste it in Voice summary (Ctrl+V) and press Summarize.

## Each time

Double-click **Voice summary.bat**. It asks:
- **the client's name** if it is a client meeting (Enter if not): you then also get the Equadis meeting
  report (PV) as a Word file, in the team's format: header, participants, objective, points discussed,
  next steps, next meeting;
- an optional subject.

Play the meeting, then press **Enter**. The summary is always in **French and English**, whatever language
was spoken. The folder `recordings/<date>_<client>/` gets `transcript.txt`, `summary.md` and the Word report,
which opens by itself. Your name for "Rédigé par" is asked once and kept in `settings.json`.

The instructions given to Claude and the Word layout are in `report.py`, shared with the desk.

- It follows the device you are listening on: plug in headphones mid-way and it keeps going.
- `--mic` also records your microphone (use it when you speak too, e.g. in a call).
- Whisper runs on the processor. `--gpu` uses an NVIDIA card instead, only if the CUDA 12 libraries are installed.
- `--model medium` transcribes better (accents, French) but slower; `tiny` is the fastest.
  The first run downloads the model.
- `--from recordings/<folder>` summarises a transcript again; `--no-summary` skips Claude.
- Windows and Linux capture the laptop sound directly. On a Mac, install BlackHole first.

If what you capture includes other people (a call), tell them it is being transcribed.

Tests: `python -m pytest app/voice` from the repository root.
