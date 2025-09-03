Perfect—here’s the “map” you asked for. It shows **each config key**, **where it’s used**, **what it changes**, and **what can go wrong**. I’ve grouped keys by section and called out CLI overrides where they exist.

# How config interacts with the code (quick primer)

* **Loader & base paths**: `utils/path_utils.load_config()` reads `config/app_config.json`. `get_downloads_directory()` uses `downloads.base_directory` (default `"downloads"`) to build `downloads/{session_uuid}/{video_uuid}/…`.&#x20;
* **Priority**: CLI flags can override parts of config (e.g., `--quality` overrides video/audio *preferred\_quality*). When a preference is missing, code continues with safe defaults.
* **Selectors**: Audio/video selection uses a scoring system (quality + format + size). Changing preferences shifts which formats are picked; bad values don’t crash, but may pick non-ideal formats.

---

# Section: `downloads`

### `downloads.base_directory` (string)

* **Used by**: `utils/path_utils.get_downloads_directory()`; the CLI driver composes final paths `{base}/{session_uuid}/{video_uuid}/{media_type}`.
* **Effect**: Changes where everything lands on disk.
* **Pitfalls**: Invalid or unwritable path → failures when creating media output dirs. The structure and examples assume this base.

### `downloads.audio.format` (e.g., `"mp3"`) and `downloads.audio.quality` (e.g., `"192"`)

* **Used by**: Audio selection path when building `preferred_formats` / `preferred_quality` (config → preferences). The code expects keys under `quality_preferences.audio`, but currently reads `downloads.audio`; missing mapping simply leaves preferences empty and falls back to defaults.
* **Effect**: Nudges `smart_audio_selection()` to prefer certain ext/bitrates. CLI `--audio` enables the download path; `--quality` can override quality.
* **Pitfalls**: Mismatch between `app_config.json` and code’s `quality_preferences.*` schema means your quality “intent” may be ignored unless you pass `--quality`. (Doesn’t crash—just different selection.)

### `downloads.video.format` (e.g., `"mp4"`) and `downloads.video.quality` (e.g., `"720p"`)

* **Used by**: Video/combined selectors (`select_default_video`, `select_combined_video_audio`) via preferences; `--quality` overrides.
* **Effect**: Biases the chosen container/resolution.
* **Pitfalls**: Same schema mismatch note as audio; still safe due to defaults.&#x20;

### `downloads.output_structure.organize_by_type` (bool)

* **Used by**: Output layout and docs assume type-based subfolders: `audio/`, `video/`, `video_with_audio/`, `transcripts/`, `metadata/`.
* **Effect**: When true (as documented), creates the clean typed folders.
* **Pitfalls**: Turning it off would require code support (docs imply true); current examples and summaries assume this structure.

---

# Section: `transcripts`

### `transcripts.processing.output_formats` (list: `clean|timestamped|structured`)

* **Used by**: Transcript pipeline to decide which files to emit. CLI `--transcript-formats` overrides.
* **Effect**: Controls which of `_clean.txt`, `_timestamped.txt`, `_structured.json` are produced.
* **Pitfalls**: Empty list → no files written even if `--transcript` set; not a crash, but “nothing created”.

### `transcripts.processing.text_cleaning.*`

* **Used by**: Cleaning stage (remove fillers, normalize whitespace, fix artifacts, list of `filler_words`).
* **Effect**: Changes LLM-readability of `_clean.txt`.
* **Pitfalls**: Over-aggressive cleaning (e.g., huge `filler_words`) can over-strip content; not a crash.&#x20;

### `transcripts.processing.chapter_detection.*`

* **Used by**: Chaptering (enabled, silence thresholds, min length, summaries).
* **Effect**: Adds chapter markers (and summaries if enabled), reflected especially in `_timestamped.txt` and structured JSON.
* **Pitfalls**: Tiny `min_silence_gap_seconds` yields noisy chapters; very large values yield none. Safe either way.&#x20;

### `transcripts.processing.preview.*`

* **Used by**: Preview path (`--preview-transcript`), line cap and quality indicators.
* **Effect**: CLI preview verbosity and stats.
* **Pitfalls**: Excessive `max_lines` → long preview output; not a crash.&#x20;

> **Selection priority note**: Transcript logic prefers CLI `--lang` → config prefs (not fully shown) → **manual captions** → EN auto → any auto. This is the documented order users will “feel.”&#x20;

---

# Section: `metadata_collection`

### `metadata_collection.enabled` (bool)

* **Used by**: Gates the entire metadata/analysis pipeline and exports.
* **Effect**: When false, skips analysis and export helpers even if other toggles are true.
* **Pitfalls**: Users may expect reports but see none; not a crash.

### `metadata_collection.content_analysis.*` (topics, sentiment, keywords, categorization, stop\_words)

* **Used by**: Content analysis within previews/structured output; CLI `--metadata-analysis` triggers it at runtime.
* **Effect**: Adds insights to preview/exports, impacts `_structured.json`, optional CSV/MD.
* **Pitfalls**: Very large `stop_words` list degrades signal; turning features off reduces fields in outputs.&#x20;

### `metadata_collection.video_metadata.*`

* **Used by**: Enriches metadata capture (channel stats, tech details, thumbnails).
* **Effect**: Adds fields to `_metadata.json` / structured export.
* **Pitfalls**: None—only affects richness of saved metadata.&#x20;

### `metadata_collection.quality_assessment.*`

* **Used by**: Quality scoring (content score, transcript confidence, A/V sync, completeness).
* **Effect**: Adds quality fields; useful for ranking/filtering.
* **Pitfalls**: If disabled, downstream tools relying on these fields should handle `None`/missing.&#x20;

### `metadata_collection.export_options.*` (`include_in_structured`, `separate_metadata_file`, `csv_summary`, `markdown_report`)

* **Used by**: Controls which export artifacts appear (`_metadata.json`, `_analysis.csv`, `_report.md`), and whether analysis is embedded in `_structured.json`.
* **Effect**: Determines which files you’ll see under `metadata/`.
* **Pitfalls**: Enabling all can generate many files; disabling all yields none (not an error).&#x20;

---

# Section: `logging`

### `logging.log_*` (downloads, format\_selections, errors, network\_requests, file\_operations)

* **Used by**: Logger calls throughout selection/download/IO paths.
* **Effect**: More/less verbosity in logs; valuable for debugging selection results, retries, IO.
* **Pitfalls**: Very chatty logs on large playlists; rotate/size limits are mentioned elsewhere, but safe.&#x20;

---

# Section: `behavior`

### `behavior.overwrite_existing_files` (bool)

* **Used by**: File write/merge steps.
* **Effect**: When false, skips writing if target exists (protects previous runs).
* **Pitfalls**: Users may think “nothing happened”—but the guard avoided overwrite. Good to surface in CLI output.&#x20;

### `behavior.sanitize_filenames` (bool), `behavior.max_filename_length` (int)

* **Used by**: Name building and sanitization; integrates with deterministic naming `Title [id].ext`.
* **Effect**: Prevents OS-illegal names; truncates long names.
* **Pitfalls**: **Windows** has extra reserved names and path length quirks; your max 255 is sensible but long nested paths can still exceed Windows limits. Keep `sanitize_filenames=true`.

### `behavior.validate_urls` (bool)

* **Used by**: Early URL validation step before extraction.
* **Effect**: Catches malformed/unsupported URLs up-front.
* **Pitfalls**: None—good UX (fewer mysterious yt-dlp errors).&#x20;

---

# Flags that override config (and how)

* `--quality 1080p`: overrides video (and in practice, combined) *preferred\_quality* for the selectors, regardless of config. Same pattern exists for audio when you wire `--quality` on `--audio` flows.&#x20;
* `--transcript-formats`: overrides `transcripts.processing.output_formats`.&#x20;
* `--outdir`: overrides the default base directory used for that run (the driver picks `args.outdir` else `get_downloads_directory()`).&#x20;

---

# Playlist controls (and how config interacts)

* **CLI only**: `--max-videos`, `--playlist-start`, `--playlist-end` drive expansion via yt-dlp `extract_flat`.
* **Effect**: Determines how many URLs land in the processing queue before downloads.
* **Pitfalls**: Current code does `min(playlist_end or float('inf'), playlist_start + max_videos - 1)`. Keep all-int math to avoid type weirdness; function still runs today, but it’s a good fix.

---

# Smart selection knobs (what changes when you tweak them)

* **Quality biasing**: Raising preferred quality increases `quality_score` weight and steers toward 1080p etc.; if not available, fallback picks closest resolution. Audio “high/med/low” maps to `format_note` heuristics.&#x20;
* **Format biasing**: Putting `"mp4"` earlier in `preferred_formats` boosts `format_score` → more MP4 picks (same for `"mp3"` on audio).&#x20;
* **Size influence**: Size contributes a smaller, inverse score; the function uses MB to subtract from 100 (different divisors for audio vs video). If filesize is unknown, it treats as `100` (neutral-to-good). This won’t crash, but can skew selection; consider clamping for predictability.

---

# Failure & “gotcha” matrix (quick reference)

| Symptom                              | Most likely key/flag                                                   | Why it happens                                                                                  | What to change                                                                 |             |                                             |
| ------------------------------------ | ---------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------ | ----------- | ------------------------------------------- |
| Nothing written under `transcripts/` | `transcripts.processing.output_formats` empty (or only unknown values) | Pipeline runs but has no targets                                                                | Add \`clean                                                                    | timestamped | structured`or use`--transcript-formats …\`  |
| Wrong video quality picked           | `downloads.video.quality` set but schema mismatch                      | Code reads `quality_preferences.video.preferred_quality` internally; missing mapping falls back | Use `--quality 1080p` for now; unify schema later                              |             |                                             |
| “Silent video” confusion             | User chose `--video-only`                                              | That path deliberately selects no-audio formats                                                 | Use `--video-with-audio` (recommended)                                         |             |                                             |
| Files show up in unexpected place    | `downloads.base_directory` or `--outdir`                               | Output root differs per run                                                                     | Standardize on one, or always pass `--outdir`                                  |             |                                             |
| Playlist unexpectedly long/short     | `--max-videos`, `--playlist-*` math                                    | Expansion logic caps range                                                                      | Set explicit `--playlist-start`/`--playlist-end`; fix math to all-int          |             |                                             |
| Oversanitized names                  | `behavior.sanitize_filenames=true` + aggressive rules                  | Safer for Windows; long titles truncated                                                        | Leave on; if you must keep long titles, ensure path length is safe on Windows  |             |                                             |

---

# Two practical next steps for you

1. **Add a `--print-config`** that shows the *effective* config after loading + CLI overrides (so you can see what the selectors will actually use). Tie it to what `select_*` expects.&#x20;
2. **Unify schema** by adding a small translation layer: map `downloads.audio/video.*` → `quality_preferences.audio/video.*` before selectors run. That removes today’s mismatch with zero risk.

If you want, I can draft the tiny shim that (a) normalizes config into `quality_preferences.*`, and (b) implements `--print-config` so you can verify the “effective” knobs before you run.
