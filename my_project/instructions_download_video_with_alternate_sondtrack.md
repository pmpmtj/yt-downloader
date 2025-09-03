## 1. Config Changes (Optional)

In `app_config.json`, add a section for audio language preferences:

```json
{
  "quality_preferences": {
    "audio": {
      "preferred_languages": ["en", "pt-PT", "pt-BR"],
      "require_language_match": false
    }
  }
}
```

* If absent, defaults are: `preferred_languages = []` (no preference) and `require_language_match = false` (allow fallback).

---

## 2. CLI Additions (`core_CLI.py`)

Add two new flags:

```python
p.add_argument(
    "--audio-lang",
    nargs="+",
    help="Preferred audio language(s), e.g., en pt-PT pt-BR. "
         "If unavailable, falls back unless --require-audio-lang is set."
)
p.add_argument(
    "--require-audio-lang",
    action="store_true",
    help="Fail if the requested audio language is not available."
)
```

---

## 3. Helper Functions (`core.py` or `format_utils.py`)

```python
def _norm_lang(code):
    if not code: return None
    return code.strip().lower().replace("_", "-")

def _fmt_audio_lang(fmt):
    return _norm_lang(fmt.get("language") or fmt.get("audio_lang") or fmt.get("lang"))

def _lang_matches(lang, preferred):
    if not preferred: return True
    if not lang: return False
    lang = _norm_lang(lang)
    prefs = [_norm_lang(x) for x in preferred]
    if lang in prefs: return True
    return any(lang.split("-")[0] == p.split("-")[0] for p in prefs)

def list_available_audio_languages(formats):
    langs = {}
    for f in formats:
        if f.get("acodec") and f.get("acodec") != "none":
            lang = _fmt_audio_lang(f) or "und"
            langs[lang] = langs.get(lang, 0) + 1
    return dict(sorted(langs.items(), key=lambda kv: (-kv[1], kv[0])))
```

* Use `list_available_audio_languages` to display audio track availability in `--info-only` mode.

---

## 4. Selection Logic

### A) Combined (video+audio) formats with language filtering

```python
def select_combined_with_lang(formats, video_prefs, preferred_langs):
    combined = [f for f in formats if is_combined_format(f)]
    if not combined: return None

    if preferred_langs:
        filtered = [f for f in combined if _lang_matches(_fmt_audio_lang(f), preferred_langs)]
        if filtered:
            return smart_video_selection(filtered, video_prefs)

    return smart_video_selection(combined, video_prefs)
```

### B) Separate video + audio merge when muxed not available

```python
def select_video_plus_audio_with_lang(formats, video_prefs, audio_prefs, preferred_langs):
    vids = [f for f in formats if is_video_format(f)]
    auds = [f for f in formats if is_audio_format(f)]

    best_video = smart_video_selection(vids, video_prefs) if vids else None
    if not best_video: return None, None

    lang_matched = [a for a in auds if _lang_matches(_fmt_audio_lang(a), preferred_langs)]
    if not lang_matched: return best_video, None

    best_audio = smart_audio_selection(lang_matched, audio_prefs)
    return best_video, best_audio
```

### C) Build format string for yt-dlp

```python
def build_format_string(video_fmt, audio_fmt):
    if video_fmt and audio_fmt:
        return f"{video_fmt['format_id']}+{audio_fmt['format_id']}"
    return video_fmt['format_id'] if video_fmt else None
```

---

## 5. Integration Flow (`core.py`)

In the `--video-with-audio` handling logic:

```python
preferred_langs = args.audio_lang or config.get("quality_preferences", {}).get("audio", {}).get("preferred_languages", [])
require_lang = args.require_audio_lang or config.get("quality_preferences", {}).get("audio", {}).get("require_language_match", False)

info = get_video_info(url)
fmts = info.get("formats", [])

# First: try muxed with matching language
selected_muxed = select_combined_with_lang(fmts, config["quality_preferences"]["video"], preferred_langs)

if selected_muxed and (not preferred_langs or _lang_matches(_fmt_audio_lang(selected_muxed), preferred_langs)):
    ydl_opts["format"] = selected_muxed["format_id"]
else:
    # Second: try video+audio merge
    v, a = select_video_plus_audio_with_lang(fmts, config["quality_preferences"]["video"], config["quality_preferences"]["audio"], preferred_langs)
    if v and a:
        ydl_opts["format"] = build_format_string(v, a)
        ydl_opts.setdefault("merge_output_format", "mp4")
    elif require_lang:
        raise RuntimeError("Requested audio language not available for this video.")
    elif selected_muxed:
        # Fallback: use muxed (original language)
        ydl_opts["format"] = selected_muxed["format_id"]
```

---

## 6. User Experience

* **Default:**

```bash
python -m my_project URL --video-with-audio
```

➡️ Downloads with original audio (no change).

* **Soft preference:**

```bash
python -m my_project URL --video-with-audio --audio-lang pt-PT
```

➡️ Uses Portuguese if available, else falls back to original.

* **Strict requirement:**

```bash
python -m my_project URL --video-with-audio --audio-lang es --require-audio-lang
```

➡️ Fails if Spanish audio is not available.

* **Preview:**

```bash
python -m my_project URL --info-only
```

➡️ Displays available audio tracks (`en`, `pt-PT`, `und`, etc.).

---

## ✅ Final Notes

* yt-dlp automatically handles merging streams with ffmpeg.
* Behavior is identical to current unless `--audio-lang` is explicitly used.
* This design is robust: it covers muxed formats, fallback merging, and strict failure conditions.
* Users can see exactly what languages are available before downloading.
