# YouTube Downloader CLI - Comprehensive User Manual

## 🎯 Overview

This manual provides complete instructions for installing, configuring, and using the YouTube Downloader CLI. It includes detailed explanations of every option, configuration file structure, workflows, and troubleshooting.

---

## 🚀 Installation

### Requirements

* Python 3.10+
* Windows/Linux/macOS

### Setup

```bash
git clone <repository-url>
cd my_project
pip install -e .
```

(Optional: install testing dependencies)

```bash
pip install -e ".[test]"
```

---

## 📖 Command Reference

### Basic Command Structure

```bash
python -m my_project [URL(s)] [OPTIONS]
```

### Positional Arguments

* **urls** — YouTube video/playlist URLs (multiple allowed)

### Core Options

* `--audio` — Download audio (MP3)
* `--video-with-audio` — Download full video with audio (⭐ recommended)
* `--video-only` — Download silent video
* `--transcript` — Download transcripts
* `--info-only` — Show video info without downloading

### Transcript Options

* `--transcript-formats [clean|timestamped|structured|all]`
* `--preview-transcript`
* `--lang CODE` — Preferred transcript language (e.g., `en`, `pt-BR`, `es`)

### Metadata & Analysis

* `--metadata-analysis` — Enable content analysis
* `--metadata-export [json|csv|markdown]`

### Batch & Playlist

* `--batch-file FILE` — File with URLs
* `--max-videos N` — Limit videos from playlist
* `--playlist-start N`, `--playlist-end N`

### Output Control

* `--outdir DIR` — Save location

---

## 📚 Configuration File (`config/app_config.json`)

Key sections:

* **downloads**: output folder structure, quality defaults
* **transcripts**: preferred languages, cleaning, chapter detection
* **metadata\_collection**: analysis features, export settings
* **network**: retries, timeouts, user-agent
* **behavior**: file overwrites, sanitization, validation

---

## 📁 File Organization

```
downloads/
├── {session_uuid}/
│   └── {video_uuid}/
│       ├── audio/
│       ├── video/
│       ├── video_with_audio/
│       ├── transcripts/
│       └── metadata/
```

* **Deterministic Naming**: `Title [video_id].ext`
* **Transcript formats**: `_clean.txt`, `_timestamped.txt`, `_structured.json`
* **Metadata exports**: `_metadata.json`, `_analysis.csv`, `_report.md`

---

## 🎯 Workflows & Examples

### Quick Info

```bash
python -m my_project URL --info-only
```

### Transcript for LLM Analysis

```bash
python -m my_project URL --transcript --transcript-formats clean
```

### Video + Audio Download

```bash
python -m my_project URL --video-with-audio --quality 1080p
```

### Metadata Analysis Workflow

```bash
python -m my_project URL --transcript --metadata-analysis --metadata-export json
```

### Batch Processing

```bash
python -m my_project --batch-file urls.txt --audio --transcript
```

---

## 🧪 Testing

```bash
python run_tests.py all
python run_tests.py unit
python run_tests.py integration
```

---

## 🔧 Troubleshooting

* **No formats found** → Check video availability
* **Transcripts disabled** → Owner disabled captions
* **Wrong language** → Use `--lang CODE`
* **Large files/slow** → Adjust `--quality`

---

## 📊 Advanced Features

* **Smart transcript selection hierarchy**: CLI `--lang` > config > manual > English auto > any auto
* **Content quality scoring & LLM suitability evaluation**
* **Chapter detection and structured transcript exports**
* **Session UUIDs for organized downloads**

---

## 📄 License

MIT License
