# 📋 YouTube Downloader CLI — Quick Reference (Synced)

> Handy, compact cheatsheet of **every available flag** with examples you can run one‑by‑one for testing and debugging.
>
> ℹ️ Context: Keep the README short. For deep explanations see **[USER\_MANUAL.md](USER_MANUAL.md)**. For repo intro and setup see **[README.md](README.md)**.

---

## 🔧 Command Structure

```bash
python -m my_project [URLs...] [OPTIONS]
```

* **URLs** can be one or many (space‑separated). Playlists are supported.
* **Batch mode** via `--batch-file file.txt` (one URL per line, `#` for comments).
* If **no content flags** are provided, the tool defaults to **info/preview mode** (no download). You can also use `--info-only` explicitly.
* **Debug mode**: `--print-config` shows effective configuration and exits (no URLs needed).

---

## 🏷️ Flags — Complete List

### Core Content Selection

| Flag                 | Type | Default | What it does                           | Notes                                                  |
| -------------------- | ---- | ------- | -------------------------------------- | ------------------------------------------------------ |
| `--audio`            | flag | `False` | Download **audio only** (MP3)          | 192kbps by default (configurable)                      |
| `--video-with-audio` | flag | `False` | Download **complete video with audio** | ⭐ Recommended for general use                          |
| `--video-only`       | flag | `False` | Download **video stream only**         | ⚠️ Silent (no audio)                                   |
| `--transcript`       | flag | `False` | Download transcripts with processing   | Formats controlled by `--transcript-formats` or config |
| `--info-only`        | flag | `False` | Show info without downloading          | Default behavior when no content flags passed          |

### Transcript Options

| Flag                   | Type   | Default                 | What it does                                      | Choices / Notes                                        |
| ---------------------- | ------ | ----------------------- | ------------------------------------------------- | ------------------------------------------------------ |
| `--transcript-formats` | list   | config defaults         | Choose transcript outputs                         | `clean`, `timestamped`, `structured`, `all`            |
| `--preview-transcript` | flag   | `False`                 | Show preview + quality indicators before download | Pair with `--metadata-analysis` for insights           |
| `--lang`               | string | none (uses config/auto) | Force preferred transcript language               | e.g., `en`, `pt-BR`, `es`, `de` — **highest priority** |

### Metadata & Analysis

| Flag                  | Type   | Default | What it does                                      | Choices / Notes                                  |
| --------------------- | ------ | ------- | ------------------------------------------------- | ------------------------------------------------ |
| `--metadata-analysis` | flag   | `False` | Enable content analysis (topics/keywords/quality) | Adds insights to previews and structured exports |
| `--metadata-export`   | string | `None`  | Export metadata                                   | `json`, `csv`, `markdown`                        |

### Audio Language Selection

| Flag                   | Type   | Default | What it does                                    | Choices / Notes                                           |
| ---------------------- | ------ | ------- | ----------------------------------------------- | --------------------------------------------------------- |
| `--audio-lang`         | list   | `None`  | Preferred audio language(s)                     | e.g., `en`, `pt-PT`, `pt-BR` — falls back if unavailable |
| `--require-audio-lang` | flag   | `False` | Fail if requested audio language not available | Use with `--audio-lang` for strict language requirement  |

### Quality & Output

| Flag        | Type   | Default         | What it does                | Choices / Notes                                                      |
| ----------- | ------ | --------------- | --------------------------- | -------------------------------------------------------------------- |
| `--quality` | string | config (`720p`) | Preferred **video** quality | `144p`, `240p`, `360p`, `480p`, `720p`, `1080p` with smart fallbacks |
| `--outdir`  | string | `.`             | Output directory            | Created if missing; organized by session/video UUIDs                 |

### Batch & Playlist Control

| Flag               | Type   | Default | What it does                   | Notes                              |
| ------------------ | ------ | ------- | ------------------------------ | ---------------------------------- |
| `--batch-file`     | string | `None`  | Read URLs from a text file     | One URL per line; `#` for comments |
| `--max-videos`     | int    | `None`  | Limit playlist items processed | Works with playlist URLs           |
| `--playlist-start` | int    | `1`     | Start index within playlist    | 1‑based                            |
| `--playlist-end`   | int    | `None`  | End index within playlist      | Inclusive upper bound              |

### Debugging & Configuration

| Flag             | Type | Default | What it does                              | Notes                                     |
| ---------------- | ---- | ------- | ----------------------------------------- | ----------------------------------------- |
| `--print-config` | flag | `False` | Show effective configuration and exit     | ⚡ Debug config issues & CLI overrides   |

> 🧠 **Transcript selection priority**: `--lang` (CLI) → config preferred languages → **manual captions** → English auto → any auto. See **USER\_MANUAL.md** for details.
> 
> 🎵 **Audio language priority**: `--audio-lang` (CLI) → config preferred languages → **combined formats** → separate video+audio merge → fallback to original audio.

---

## 🧪 One‑by‑One Testing Recipes

> Replace `URL` with an actual video and `PLAYLIST_URL` with a playlist.

### Information / Preview

```bash
# Default info/preview (no downloads)
python -m my_project URL

# Explicit info only (shows available audio languages)
python -m my_project URL --info-only

# Preview transcript with insights
python -m my_project URL --preview-transcript

# Preview + metadata analysis
python -m my_project URL --preview-transcript --metadata-analysis
```

### Core Downloads

```bash
# Recommended: complete video with audio
python -m my_project URL --video-with-audio

# Video only (silent)
python -m my_project URL --video-only

# Audio only (MP3)
python -m my_project URL --audio
```

### Audio Language Selection

```bash
# Prefer Portuguese audio (falls back to original if unavailable)
python -m my_project URL --video-with-audio --audio-lang pt-PT

# Multiple language preferences (priority order)
python -m my_project URL --video-with-audio --audio-lang en pt-PT pt-BR

# Strict language requirement (fails if Spanish not available)
python -m my_project URL --video-with-audio --audio-lang es --require-audio-lang

# Check available audio languages before downloading
python -m my_project URL --info-only

# Audio-only download with language preference
python -m my_project URL --audio --audio-lang pt-PT

# Multiple videos with consistent audio language preference
python -m my_project URL1 URL2 URL3 --video-with-audio --audio-lang en
```

### Quality & Output

```bash
# Force 1080p for video with audio
python -m my_project URL --video-with-audio --quality 1080p

# Save to a specific folder
python -m my_project URL --video-with-audio --outdir ./downloads
```

### Transcripts

```bash
# All defaults from config
python -m my_project URL --transcript

# Clean text only (LLM‑ready)
python -m my_project URL --transcript --transcript-formats clean

# Clean + structured JSON
python -m my_project URL --transcript --transcript-formats clean structured

# Force language (overrides everything)
python -m my_project URL --transcript --lang pt-BR
```

### Metadata & Exports

```bash
# Enable analysis
python -m my_project URL --metadata-analysis

# Export metadata JSON
python -m my_project URL --transcript --metadata-export json

# Export CSV summary
python -m my_project URL --transcript --metadata-export csv

# Export Markdown report
python -m my_project URL --transcript --metadata-export markdown
```

### Batch & Playlist

```bash
# Batch file (one URL per line)
python -m my_project --batch-file urls.txt --audio

# First 10 videos of a playlist
python -m my_project PLAYLIST_URL --max-videos 10 --video-with-audio

# Range within playlist (5 to 15)
python -m my_project PLAYLIST_URL --playlist-start 5 --playlist-end 15 --transcript
```

### Combined Features

```bash
# High-quality video with Portuguese audio and transcripts
python -m my_project URL --video-with-audio --quality 1080p --audio-lang pt-PT --transcript

# Audio language + metadata export
python -m my_project URL --video-with-audio --audio-lang es --metadata-export json

# Batch download with preferred audio language
python -m my_project --batch-file urls.txt --video-with-audio --audio-lang en

# Strict language requirement with custom output folder
python -m my_project URL --video-with-audio --audio-lang pt-BR --require-audio-lang --outdir ./portuguese-videos
```

### Debugging & Configuration

```bash
# See current effective configuration
python -m my_project --print-config

# Debug config with CLI overrides
python -m my_project --print-config --quality 1080p --outdir ./custom

# Check transcript format settings
python -m my_project --print-config --transcript-formats clean structured

# Verify all settings including audio language preferences
python -m my_project --print-config --video-with-audio --quality 720p --audio-lang pt-PT --transcript
```

---

## 📁 What to Expect in Outputs

* **Directories**: `audio/`, `video/`, `video_with_audio/`, `transcripts/`, `metadata/`
* **Naming**: `Title [video_id].ext` (deterministic, safe for DB joins)
* **Transcript files**: `*_clean.txt`, `*_timestamped.txt`, `*_structured.json`
* **Metadata files**: `*_metadata.json`, `*_analysis.csv`, `*_report.md`

---

## 🧷 Tips & Gotchas

* `--video-only` is **silent** by design. Use `--video-with-audio` for normal viewing.
* Passing multiple content flags is allowed (e.g., `--audio --video-with-audio --transcript`).
* If a preferred quality/format isn't available, the tool **falls back intelligently**.
* Use `--lang CODE` to guarantee transcript language when available.
* Audio language selection works with `--video-with-audio` — tries combined formats first, then merges separate streams.
* `--audio-lang` accepts multiple languages in priority order (first available wins).
* Without `--require-audio-lang`, the tool falls back to original audio if preferred language unavailable.

### 🔍 When to Use `--print-config`

* **Before first run**: Check what settings are actually loaded from your config
* **Quality issues**: Videos not downloading in expected quality? Verify effective settings
* **Path problems**: Files going to wrong directory? See the actual output paths
* **Transcript troubles**: No transcript files created? Check format configuration
* **CLI override testing**: Confirm your `--quality`, `--outdir` flags are working
* **Schema migration**: After config changes, verify normalization worked correctly

---

## 🔗 See Also

* **[README.md](README.md)** – short overview, install, and quick start
* **[USER\_MANUAL.md](USER_MANUAL.md)** – deep dive: configuration, workflows, troubleshooting
