Of course. Mastering the configuration is key to leveraging the full power of your project. Here is a comprehensive map of the configuration keys, which scripts use them, and how they affect the outcome.

***

## Configuration Flow Overview 🗺️

The application's behavior is primarily driven by the `config/app_config.json` file. When you run a command, the configuration is loaded by various modules to determine how to select formats, process text, name files, and what metadata to collect.

1.  **`core_CLI.py`**: This is the main entry point. [cite_start]It reads the config to set up download paths, determine default behaviors (like which transcript formats to output), and enable/disable major features like metadata collection[cite: 205, 216].
2.  [cite_start]**`core.py`**: This script uses the `quality_preferences` to intelligently score and select the best audio and video formats[cite: 106, 110]. [cite_start]It also reads `transcripts.preferred_languages` to guide its default transcript selection[cite: 120].
3.  [cite_start]**`yt_downloads_utils.py`**: It reads the `downloads.filename_template` and `network` settings to handle the actual downloading process with `yt-dlp`, including naming conventions and retry logic[cite: 636, 172].
4.  [cite_start]**`transcript_processor.py`**: This class is heavily configured by the `transcripts.processing` section to perform tasks like text cleaning, chapter detection, and preview generation[cite: 580, 581, 588, 617].
5.  [cite_start]**`metadata_collector.py`**: This class uses the `metadata_collection` section as a set of feature flags to decide which analyses to run, such as keyword extraction or quality assessment[cite: 356, 383, 382].

---

## Configuration Key Map

### `downloads` 📁

This section controls where and how files are saved.

| Key | Used In | Purpose & Effect |
| :-- | :-- | :-- |
| `base_directory` | `path_utils.py`, `core_CLI.py` | [cite_start]Sets the root folder for all downloads[cite: 1, 290]. Changing `"downloads"` to `"./media"` will save everything in a `media` folder in your current directory. |
| `folder_structure` | `path_utils.py`, `core_CLI.py` | [cite_start]Defines the subdirectory structure for each video[cite: 1, 290]. [cite_start]It's used to create organized, session-specific folders[cite: 480]. If you set it to `"{media_type}"`, all audio will go into one `audio` folder, etc., removing the UUID separation. |
| `filename_template` | `yt_downloads_utils.py` | **Crucial key**. [cite_start]Controls the naming of all downloaded media files (`.mp4`, `.mp3`)[cite: 1, 636]. The default `%(title)s [%(id)s].%(ext)s` ensures unique filenames. Changing it to `%(uploader)s - %(title)s.%(ext)s` could cause name collisions if an uploader posts videos with the same title. |

### `quality_preferences` ⭐

This section governs the smart format selection logic.

| Key | Used In | Purpose & Effect |
| :-- | :-- | :-- |
| `video.preferred_quality` | `core.py` | [cite_start]Sets the target video quality (e.g., "720p")[cite: 1]. [cite_start]The logic will score formats matching this quality highest[cite: 92]. Changing this to "1080p" will prioritize 1080p downloads. |
| `video.fallback_qualities` | `core.py` | [cite_start]A list of acceptable qualities used for scoring if the preferred one isn't available[cite: 1]. Removing `"1080p"` from the list would make the selector prefer lower-quality options over 1080p if 720p is unavailable. |
| `video.preferred_formats` | `core.py` | [cite_start]A prioritized list of file extensions (e.g., "mp4", "webm")[cite: 2, 101]. [cite_start]The selection logic scores formats with these extensions higher[cite: 95]. Changing the order will change the preferred container format. |
| `audio.preferred_quality` | `core.py` | [cite_start]Sets the target audio quality ("medium", "high", "low")[cite: 2]. [cite_start]The logic scores formats based on this preference[cite: 90]. |
| `audio.preferred_codec` | Not explicitly used in the scoring logic but could be added. [cite_start]The post-processor in `yt_downloads_utils.py` forces the output to `mp3` with a bitrate of `192` regardless of this key[cite: 638, 2]. |
| `*.max_fallback_attempts` | `core.py`, `core_CLI.py` | [cite_start]Determines how many of the top-scored formats the tool will attempt to download before giving up[cite: 2, 3, 172, 176]. Setting this to `1` means if the absolute best format fails, the download fails, even if other good options exist. |

### `transcripts` 📄

This section dictates all aspects of transcript processing and output.

| Key | Used In | Purpose & Effect |
| :-- | :-- | :-- |
| `preferred_languages` | `core.py` | [cite_start]A prioritized list of language codes (e.g., `en`, `en-US`)[cite: 5]. [cite_start]This is the **highest priority** for automatic transcript selection after the `--lang` CLI flag[cite: 78, 120]. Changing `["en", "es"]` to `["es", "en"]` will make the tool default to Spanish transcripts over English if both are available. |
| `processing.<...>.enabled` | `transcript_processor.py` | [cite_start]Master switches for `text_cleaning` and `chapter_detection`[cite: 581, 588]. Setting `text_cleaning.enabled` to `false` will result in a "clean" transcript file that contains all the raw filler words ("um", "uh", etc.). |
| `processing.output_formats` | `core_CLI.py` | [cite_start]Determines which transcript files (`clean`, `timestamped`, `structured`) are generated by default when you use the `--transcript` flag without specifying `--transcript-formats`[cite: 5, 206]. If you remove `"clean"`, the `_clean.txt` file won't be created unless you explicitly request it with the CLI flag. |
| `processing.text_cleaning.filler_words` | `transcript_processor.py` | [cite_start]The list of words to be removed from the "clean" transcript[cite: 7, 582]. You can add custom words here like corporate jargon to automatically scrub them from your transcripts. **Crashing**: An invalid list or non-string elements might cause a regex error. |
| `processing.chapter_detection.min_silence_gap_seconds` | `transcript_processor.py` | [cite_start]The minimum pause duration between transcript entries that signifies a new chapter[cite: 8, 588]. Increasing this from `3.0` to `10.0` will result in fewer, longer chapters being detected. |
| `processing.preview.<...>` | `transcript_processor.py` | [cite_start]Controls the output of the `--preview-transcript` flag, including how many lines are shown (`max_lines`) and whether stats are included (`include_stats`)[cite: 8, 9, 617]. |

### `metadata_collection` 🔬

Controls the rich analysis features.

| Key | Used In | Purpose & Effect |
| :-- | :-- | :-- |
| `enabled` | `core_CLI.py`, `transcript_processor.py` | [cite_start]A global switch to turn all metadata analysis on or off[cite: 143, 611]. If `false`, no content analysis, quality assessment, or keyword extraction will run, even if specified in the CLI. This provides a way to speed up downloads significantly. |
| `content_analysis.extract_keywords` | `metadata_collector.py` | [cite_start]A feature flag to enable/disable keyword extraction from the transcript[cite: 10, 383]. Setting to `false` will result in an empty `keywords` list in the metadata exports. |
| `content_analysis.stop_words` | `metadata_collector.py` | [cite_start]The list of common words to ignore during keyword extraction[cite: 10, 11, 358]. Adding words to this list will prevent them from being identified as keywords. |
| `quality_assessment.content_quality_score` | `metadata_collector.py` | [cite_start]A feature flag to enable/disable the calculation of a quality score for the transcript content[cite: 13, 382]. Disabling this will remove the score from previews and metadata reports. |

### `network` 🌐

Governs network behavior and resilience.

| Key | Used In | Purpose & Effect |
| :-- | :-- | :-- |
| `max_retries` | `yt_downloads_utils.py`, `core_CLI.py` | [cite_start]The number of times to retry a failed download[cite: 3, 172]. Essential for unstable connections. |
| `retry_delay_seconds` | `yt_downloads_utils.py`, `core_CLI.py` | [cite_start]The initial delay (in seconds) before the first retry[cite: 4, 172]. [cite_start]The delay increases exponentially for subsequent retries[cite: 640]. |
| `user_agent` | Not currently implemented | This key is present in the config but is not passed to the `yt-dlp` constructor in the provided scripts. If implemented, it would allow spoofing the browser identity to circumvent potential blocks. |

### `behavior` ✅

Controls file operations and validation.

| Key | Used In | Purpose & Effect |
| :-- | :-- | :-- |
| `overwrite_existing_files` | Not currently implemented | This key is present but the corresponding `yt-dlp` option (`--no-overwrites`) is not set in the download functions. Currently, `yt-dlp`'s default behavior (which is to not overwrite) is used. |
| `sanitize_filenames` | Not currently implemented | This is a `yt-dlp` option that is enabled by default. While the config key exists, the scripts don't explicitly set it, relying on the default safe behavior. |
| `validate_urls` | Not currently implemented | [cite_start]The config key exists, but there is no explicit validation logic tied to this flag in `core_CLI.py` before processing URLs[cite: 15]. The tool currently relies on `yt-dlp` to handle invalid URLs. |