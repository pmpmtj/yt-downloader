# 📋 YouTube Downloader CLI - Quick Reference

## **Command Structure**
```bash
python -m my_project [URLs...] [OPTIONS]
```

## **CLI Arguments & Flags**

| **Flag** | **Type** | **Default** | **Description** | **Examples** |
|----------|----------|-------------|-----------------|--------------|
| `urls` | positional | *required* | YouTube video URL(s) or playlist URL(s) to process | `https://youtube.com/watch?v=xyz` |

### **🎵 Download Type Options**
| **Flag** | **Type** | **Default** | **Description** | **Notes** |
|----------|----------|-------------|-----------------|-----------|
| `--audio` | flag | `False` | Download audio only (MP3 format) | 192kbps quality |
| `--video` | flag | `False` | Download video only (⚠️ **silent - no audio**) | Video-only stream |
| `--video-with-audio` | flag | `False` | Download video with audio included | ⭐ **Recommended** |
| `--transcript` | flag | `False` | Download enhanced transcripts | Multiple formats available |

### **🎯 Quality & Language Options**
| **Flag** | **Type** | **Default** | **Description** | **Examples** |
|----------|----------|-------------|-----------------|--------------|
| `--quality` | string | `None` (uses config: `720p`) | Preferred video quality | `720p`, `1080p`, `480p` |
| `--lang` | string | `None` (auto-detect) | Preferred transcript/audio language | `en`, `pt-BR`, `es` |

### **📄 Transcript Options**
| **Flag** | **Type** | **Default** | **Description** | **Choices** |
|----------|----------|-------------|-----------------|-------------|
| `--transcript-formats` | list | `None` (uses config defaults) | Transcript formats to generate | `clean`, `timestamped`, `structured`, `all` |
| `--preview-transcript` | flag | `False` | Show transcript preview before downloading | Quality indicators included |

### **📊 Metadata & Analysis**
| **Flag** | **Type** | **Default** | **Description** | **Choices** |
|----------|----------|-------------|-----------------|-------------|
| `--metadata-analysis` | flag | `False` | Enable comprehensive content analysis | Keywords, topics, quality assessment |
| `--metadata-export` | string | `None` | Export metadata to specified format | `json`, `csv`, `markdown` |

### **🎬 Batch Processing**
| **Flag** | **Type** | **Default** | **Description** | **Examples** |
|----------|----------|-------------|-----------------|--------------|
| `--batch-file` | string | `None` | File containing URLs (one per line) | `urls.txt` |
| `--max-videos` | integer | `None` (no limit) | Maximum number of videos from playlists | `10`, `50` |
| `--playlist-start` | integer | `1` | Playlist video to start at | `1`, `5`, `10` |
| `--playlist-end` | integer | `None` (process all) | Playlist video to end at | `20`, `100` |

### **📁 Output Options**
| **Flag** | **Type** | **Default** | **Description** | **Notes** |
|----------|----------|-------------|-----------------|-----------|
| `--outdir` | string | `.` (current directory) | Directory to save downloaded files | Creates UUID-based structure |
| `--info-only` | flag | `False` | Only fetch and display info (no download) | Preview mode |

## **📋 Configuration Defaults** (from `app_config.json`)

### **🎵 Audio Defaults:**
- **Quality**: `medium` (192kbps)
- **Format**: `mp3` (fallback: `m4a`, `ogg`)
- **Retries**: 3 attempts with exponential backoff

### **🎬 Video Defaults:**
- **Quality**: `720p` (fallback: `480p`, `360p`, `1080p`)
- **Format**: `mp4` (fallback: `webm`, `mkv`)
- **Retries**: 3 attempts with exponential backoff

### **📄 Transcript Defaults:**
- **Languages**: `["en", "en-US", "en-GB"]`
- **Formats**: `clean`, `timestamped`, `structured` (all enabled)
- **Processing**: Text cleaning, chapter detection enabled

## **🚀 Quick Start Examples**

### **Basic Usage:**
```bash
# Information only
python -m my_project https://youtube.com/watch?v=xyz --info-only

# Download video with audio (recommended)
python -m my_project https://youtube.com/watch?v=xyz --video-with-audio

# Download audio with transcript
python -m my_project https://youtube.com/watch?v=xyz --audio --transcript
```

### **Advanced Usage:**
```bash
# High-quality download with all transcript formats
python -m my_project https://youtube.com/watch?v=xyz --video-with-audio --transcript --transcript-formats all --quality 1080p

# LLM analysis workflow
python -m my_project https://youtube.com/watch?v=xyz --transcript --metadata-analysis --metadata-export json

# Batch processing with preview
python -m my_project --batch-file urls.txt --preview-transcript --outdir ./downloads
```

### **Playlist Processing:**
```bash
# Process first 10 videos of playlist
python -m my_project https://youtube.com/playlist?list=xyz --max-videos 10 --audio --transcript

# Process videos 5-15 from playlist
python -m my_project https://youtube.com/playlist?list=xyz --playlist-start 5 --playlist-end 15 --video-with-audio
```

## **💡 Pro Tips**

1. **⭐ Recommended**: Use `--video-with-audio` for complete video files
2. **🔍 Preview**: Use `--preview-transcript` to check content quality first
3. **📊 Analysis**: Combine `--metadata-analysis` with `--metadata-export json` for LLM workflows
4. **🎯 Quality**: Specify `--quality 720p` for consistent quality across videos
5. **📁 Organization**: Files are organized by session/video UUIDs automatically

## **⚠️ Important Notes**

- **`--video` flag produces silent videos** (video-only streams without audio)
- **`--video-with-audio` is recommended** for complete video files
- **Multiple URLs supported**: Space-separated on command line
- **Batch files**: One URL per line, `#` for comments
- **UUID Organization**: All downloads organized by session and video UUIDs
- **Fallback Logic**: Automatic quality/format fallbacks if preferred options fail

## **📁 Output File Structure**

```
downloads/
├── {session_uuid}/
│   └── {video_uuid}/
│       ├── audio/
│       │   └── video_title.mp3
│       ├── video/
│       │   └── video_title.mp4              # ⚠️ Silent video only
│       ├── video_with_audio/
│       │   └── video_title.mp4              # ⭐ Complete video
│       ├── transcripts/
│       │   ├── video_id_en_clean.txt        # LLM-optimized
│       │   ├── video_id_en_timestamped.txt  # Reference format
│       │   └── video_id_en_structured.json  # Machine-readable
│       └── metadata/
│           ├── video_id_metadata.json       # Comprehensive metadata
│           ├── video_id_analysis.csv        # Analysis summary
│           └── video_id_report.md           # Human-readable report
```

## **🔧 Common Workflows**

### **Content Analysis Workflow:**
```bash
# 1. Preview content
python -m my_project URL --preview-transcript --metadata-analysis

# 2. Download for analysis
python -m my_project URL --transcript --transcript-formats clean structured --metadata-export json

# 3. Batch process playlist
python -m my_project PLAYLIST_URL --max-videos 20 --transcript --metadata-export csv
```

### **Media Archiving Workflow:**
```bash
# High-quality complete downloads
python -m my_project URL --video-with-audio --audio --transcript --quality 1080p --outdir ./archive

# Batch playlist archiving
python -m my_project PLAYLIST_URL --video-with-audio --transcript --transcript-formats all --outdir ./archive
```

### **Quick Audio Collection:**
```bash
# Audio-only with transcripts
python -m my_project URL --audio --transcript --transcript-formats clean

# Batch audio from file
python -m my_project --batch-file podcast_urls.txt --audio --transcript
```

---

**Generated for YouTube Downloader CLI v1.0**  
**Last Updated**: $(date)  
**Project**: [YouTube Downloader with Enhanced Transcript Processing]
