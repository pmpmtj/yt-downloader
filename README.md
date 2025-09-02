# YouTube Downloader CLI

A command-line tool for downloading YouTube videos, audio, and transcripts with advanced processing and AI-ready exports.

## ✨ Features

* Download audio (MP3), video (MP4), and transcripts
* Smart format and quality selection
* Rich metadata collection and LLM-ready exports (JSON/CSV/Markdown)
* Batch processing and playlist support
* Cross-platform (Windows/Linux/macOS)

## 🚀 Installation

```bash
git clone <repository-url>
cd my_project
pip install -e .
```

## 📖 Quick Start

```bash
# Info only (no download)
python -m my_project URL --info-only

# Download video with audio (recommended)
python -m my_project URL --video-with-audio

# Audio with transcripts
python -m my_project URL --audio --transcript
```

## 📚 Documentation

* ⚡ [CLI Quick Reference](CLI_QUICK_REFERENCE.md) — Cheatsheet of commands and flags
* 📖 [User Manual](USER_MANUAL.md) — Full details, examples, configuration, workflows, troubleshooting

## 🧪 Testing

```bash
pip install -e ".[test]"
python run_tests.py all
```

## 📄 License

MIT License
