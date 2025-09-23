# YouTube Transcript Downloader

A standalone Python script that downloads YouTube video transcripts in 3 different formats optimized for various use cases.

## Features

- **3 Output Formats**:
  - **Clean Text** - Optimized for LLM analysis with filler words removed
  - **Timestamped Text** - Original format with timestamps for each segment
  - **Structured JSON** - Rich metadata with chapters, statistics, and analysis

- **Smart Transcript Selection** - Automatically selects the best available transcript (manual > auto-generated, English preferred)
- **No Configuration Required** - Works out of the box with sensible defaults
- **Cross-platform** - Works on Windows, macOS, and Linux
- **Command-line Interface** - Easy to use and integrate into workflows

## Installation

### Prerequisites

- Python 3.7 or higher
- Internet connection

### Dependencies

Install the required packages:

```bash
pip install yt-dlp youtube-transcript-api
```

Or install from the project's requirements.txt:

```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

```bash
python dl_transcription.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

### Advanced Usage

```bash
# Specify output directory
python dl_transcription.py "https://youtu.be/dQw4w9WgXcQ" --output-dir ./transcripts

# Enable verbose logging
python dl_transcription.py "https://youtu.be/dQw4w9WgXcQ" --verbose

# Show help
python dl_transcription.py --help
```

### Command-line Options

- `url` - YouTube video URL (required)
- `--output-dir`, `-o` - Output directory (defaults to current directory)
- `--verbose`, `-v` - Enable verbose logging
- `--help`, `-h` - Show help message

## Output Files

The script generates 3 files for each video:

### 1. Clean Text (`*_clean.txt`)
- Text optimized for LLM analysis
- Filler words removed (um, uh, like, etc.)
- Whitespace normalized
- Transcription artifacts fixed
- Perfect for AI/ML processing

### 2. Timestamped Text (`*_timestamped.txt`)
- Original transcript format with timestamps
- Format: `[123.45s] transcript text`
- Useful for video editing and synchronization
- Preserves original timing information

### 3. Structured JSON (`*_structured.json`)
- Rich metadata and analysis
- Video information (title, duration, uploader, etc.)
- Chapter detection and summaries
- Content statistics (word count, reading time, etc.)
- Quality assessment
- Perfect for data analysis and reporting

## File Naming Convention

Files are named using the pattern:
```
{video_id}_{language_code}_{safe_title}_{format}.{extension}
```

Example:
```
dQw4w9WgXcQ_en_Rick Astley - Never Gonna Give You Up Official Vid_clean.txt
dQw4w9WgXcQ_en_Rick Astley - Never Gonna Give You Up Official Vid_timestamped.txt
dQw4w9WgXcQ_en_Rick Astley - Never Gonna Give You Up Official Vid_structured.json
```

## Supported Video Sources

- YouTube (youtube.com)
- YouTube Shorts (youtube.com/shorts)
- YouTube Music (music.youtube.com)
- Any URL supported by yt-dlp

## Transcript Language Selection

The script automatically selects the best available transcript:

1. **Manual transcripts** (preferred over auto-generated)
2. **English language** (if available)
3. **Auto-generated transcripts** (fallback)
4. **Any available language** (last resort)

## Error Handling

The script includes comprehensive error handling for:
- Invalid YouTube URLs
- Videos without transcripts
- Network connectivity issues
- File system permissions
- Missing dependencies

## Examples

### Download a single video
```bash
python dl_transcription.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

### Download to specific directory
```bash
python dl_transcription.py "https://youtu.be/dQw4w9WgXcQ" --output-dir ./my_transcripts
```

### Batch processing (using shell)
```bash
# Windows PowerShell
$urls = @(
    "https://www.youtube.com/watch?v=video1",
    "https://www.youtube.com/watch?v=video2",
    "https://www.youtube.com/watch?v=video3"
)
foreach ($url in $urls) {
    python dl_transcription.py $url --output-dir ./batch_transcripts
}
```

```bash
# Linux/macOS
for url in "https://www.youtube.com/watch?v=video1" "https://www.youtube.com/watch?v=video2"; do
    python dl_transcription.py "$url" --output-dir ./batch_transcripts
done
```

## Troubleshooting

### Common Issues

1. **"No module named 'youtube_transcript_api'"**
   ```bash
   pip install youtube-transcript-api
   ```

2. **"No suitable transcript found"**
   - The video may not have transcripts available
   - Try a different video or check if transcripts are enabled

3. **"Failed to extract video info"**
   - Check if the URL is valid
   - Ensure you have internet connectivity
   - The video may be private or region-restricted

4. **Permission denied errors**
   - Check if you have write permissions to the output directory
   - Try running with administrator privileges if needed

### Debug Mode

Use the `--verbose` flag to see detailed logging information:

```bash
python dl_transcription.py "https://youtu.be/dQw4w9WgXcQ" --verbose
```

## Technical Details

### Dependencies
- `yt-dlp` - YouTube video metadata extraction
- `youtube-transcript-api` - Transcript fetching
- `argparse` - Command-line argument parsing
- `pathlib` - Cross-platform path handling
- `json` - JSON file generation

### Architecture
- **Modular design** - Separate modules for different functionality
- **Error resilience** - Graceful handling of API failures
- **Cross-platform** - Works on Windows, macOS, and Linux
- **Self-contained** - No external configuration files required

## License

This project is part of a larger YouTube downloader application. Please refer to the main project license for usage terms.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## Support

For issues and questions:
1. Check the troubleshooting section above
2. Review the error messages and logs
3. Ensure all dependencies are installed
4. Verify the YouTube URL is accessible

---

**Note**: This tool is for educational and personal use only. Please respect YouTube's Terms of Service and copyright laws when using this tool.
