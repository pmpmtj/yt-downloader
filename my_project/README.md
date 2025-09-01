# YouTube Downloader CLI

A robust command-line tool for downloading YouTube content including audio, video, and transcripts with intelligent format selection and fallback mechanisms.

## Features

- **Multi-format Support**: Download audio (MP3), video (MP4), and transcripts
- **Smart Format Selection**: Automatic selection of optimal formats with fallback options
- **Transcript Support**: Download subtitles/captions in multiple languages
- **Flexible Output**: Customizable download directories and file organization
- **Information Mode**: Preview available formats without downloading

## Installation

### From Source
```bash
cd my_project
pip install -e .
```

### Dependencies
```bash
pip install yt-dlp youtube-transcript-api colorama
```

## Usage

### Basic Usage
```bash
# Download video info only (no download)
python -m my_project https://youtube.com/watch?v=VIDEO_ID

# Download audio only
python -m my_project https://youtube.com/watch?v=VIDEO_ID --audio

# Download video only  
python -m my_project https://youtube.com/watch?v=VIDEO_ID --video

# Download transcript only
python -m my_project https://youtube.com/watch?v=VIDEO_ID --transcript

# Download everything
python -m my_project https://youtube.com/watch?v=VIDEO_ID --audio --video --transcript
```

### CLI Arguments

#### Required Arguments
- `url` - YouTube video URL to process

#### Optional Arguments
- `--lang LANGUAGE` - Preferred transcript/audio language (e.g., en, pt-BR, es)
- `--quality QUALITY` - Preferred video quality (e.g., 720p, 1080p, 480p)
- `--audio` - Download audio only
- `--video` - Download video only
- `--transcript` - Download transcript only (if available)
- `--info-only` - Only fetch and display info (no download)
- `--outdir DIRECTORY` - Directory to save downloaded files (default: current directory)

### Examples

#### Information Only
```bash
# Show all available formats and metadata
python -m my_project https://youtube.com/watch?v=dQw4w9WgXcQ --info-only
```

#### Download with Preferences
```bash
# Download 720p video with English transcript
python -m my_project https://youtube.com/watch?v=dQw4w9WgXcQ --video --transcript --quality 720p --lang en

# Download audio with Portuguese transcript
python -m my_project https://youtube.com/watch?v=dQw4w9WgXcQ --audio --transcript --lang pt-BR

# Download to specific directory
python -m my_project https://youtube.com/watch?v=dQw4w9WgXcQ --audio --outdir ./downloads
```

#### Multiple Downloads
```bash
# Download all media types
python -m my_project https://youtube.com/watch?v=dQw4w9WgXcQ --audio --video --transcript --outdir ./my_downloads
```

## Output

### Information Mode
When run with `--info-only` or no download flags, the tool displays:
- Video metadata (title, uploader, duration, view count, upload date)
- Available audio formats with quality information
- Available video formats with resolution and codec details
- Available transcript languages and types (manual vs auto-generated)
- Selected default formats for each media type

### Download Mode
- Audio files are saved as MP3 with 192kbps quality
- Video files maintain original format and quality
- Transcripts are saved as text files with timestamps
- Files are named using the video title

### File Naming Convention
- Audio: `{video_title}.mp3`
- Video: `{video_title}.{original_extension}`
- Transcript: `{video_id}_{language_code}.txt`

## Format Selection Logic

The tool automatically selects the best available formats:

### Audio Selection
1. Prioritizes formats marked as "default"
2. Filters for audio-only streams (no video codec)
3. Prefers higher quality audio codecs

### Video Selection  
1. Prioritizes formats marked as "default"
2. Filters for video-only streams (no audio codec)
3. Considers quality preferences if specified

### Transcript Selection
1. Looks for manual transcripts first
2. Falls back to auto-generated if available
3. Respects language preferences
4. Shows translatable options

## Troubleshooting

### Common Issues
- **"No formats found"**: Video may be private, deleted, or region-locked
- **"Transcripts disabled"**: Video owner has disabled captions
- **"Download failed"**: Check internet connection and video availability

### Testing the Tool
```bash
# Test with a known working video
python -m my_project https://youtube.com/watch?v=dQw4w9WgXcQ --info-only

# Test audio download
python -m my_project https://youtube.com/watch?v=dQw4w9WgXcQ --audio --outdir ./test_downloads

# Test with quality preference
python -m my_project https://youtube.com/watch?v=dQw4w9WgXcQ --video --quality 480p --info-only
```

## Development Status

This project is in active development. Current features are stable for CLI usage. Future enhancements will include:
- Web interface integration
- Batch processing and playlist support
- Enhanced error handling and retry mechanisms
- UUID-based file organization
- Configuration file support

## Requirements

- Python 3.10+
- yt-dlp
- youtube-transcript-api
- colorama

## License

MIT