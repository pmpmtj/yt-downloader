# YouTube Downloader CLI

A sophisticated command-line tool for downloading YouTube content with advanced transcript processing, metadata analysis, and LLM-ready export capabilities. Features intelligent format selection, comprehensive content analysis, and production-ready testing framework.

## ✨ Features

### Core Functionality
- **Multi-format Support**: Download audio (MP3), video (MP4), and enhanced transcripts
- **Smart Format Selection**: Intelligent scoring system with fallback mechanisms
- **Advanced Transcript Processing**: Text cleaning, chapter detection, multiple output formats
- **Rich Metadata Collection**: Content analysis, quality assessment, and comprehensive video metadata
- **LLM-Ready Exports**: Structured JSON, CSV summaries, and Markdown reports

### Enhanced Capabilities
- **Preview Mode**: Preview transcripts with quality indicators before download
- **Content Analysis**: Topic extraction, sentiment analysis, keyword identification
- **Quality Assessment**: Content quality scoring and LLM suitability evaluation
- **Batch Processing**: Handle multiple URLs and playlists efficiently
- **Configuration-Driven**: Centralized JSON configuration for all preferences

## 🚀 Installation

### Prerequisites
- **Python 3.10+** required
- **Windows/Linux/macOS** compatible

### Quick Start
```bash
# Clone and install
git clone <repository-url>
cd my_project
pip install -e .

# Install with testing dependencies (optional)
pip install -e ".[test]"
```

### Dependencies
Core dependencies are automatically installed:
```bash
# Core functionality
yt-dlp>=2023.7.6          # YouTube download engine
youtube-transcript-api>=0.6.0  # Transcript extraction
colorama>=0.4.6           # Cross-platform colored output

# Testing (optional)
pytest>=7.4.0             # Testing framework
pytest-cov>=4.1.0         # Coverage reporting
```

## 📖 Usage

### Quick Start Examples
```bash
# Download video info only (no download)
python -m my_project https://www.youtube.com/watch?v=KYT3NiqI-X8

# Download audio with enhanced transcript processing
python -m my_project https://www.youtube.com/watch?v=KYT3NiqI-X8 --audio --transcript

# Preview transcript with quality analysis before download
python -m my_project https://www.youtube.com/watch?v=KYT3NiqI-X8 --preview-transcript

# Download with comprehensive metadata analysis
python -m my_project https://www.youtube.com/watch?v=KYT3NiqI-X8 --audio --transcript --metadata-analysis --metadata-export json

# LLM-ready structured export
python -m my_project https://www.youtube.com/watch?v=KYT3NiqI-X8 --transcript --transcript-formats clean timestamped structured
```

### CLI Arguments Reference

#### Required Arguments
- `url` - YouTube video URL to process

#### Core Download Options
- `--audio` - Download audio (MP3 format)
- `--video` - Download video (original format)
- `--transcript` - Download enhanced transcripts
- `--info-only` - Display comprehensive info without downloading

#### Enhanced Transcript Options
- `--transcript-formats FORMAT [FORMAT ...]` - Output formats: `clean`, `timestamped`, `structured`
- `--preview-transcript` - Preview transcript with quality indicators
- `--lang LANGUAGE` - Preferred language (e.g., en, pt-BR, es)

#### Metadata & Analysis
- `--metadata-analysis` - Enable comprehensive content analysis
- `--metadata-export FORMAT` - Export metadata: `json`, `csv`, `markdown`

#### General Options
- `--quality QUALITY` - Video quality preference (720p, 1080p, 480p)
- `--outdir DIRECTORY` - Output directory (default: current directory)
- `--batch-file FILE` - Process multiple URLs from file

### Detailed Examples

#### Information & Preview
```bash
# Comprehensive video information
python -m my_project https://www.youtube.com/watch?v=KYT3NiqI-X8 --info-only

# Preview transcript with quality analysis
python -m my_project https://www.youtube.com/watch?v=KYT3NiqI-X8 --preview-transcript

# Preview with metadata insights
python -m my_project https://www.youtube.com/watch?v=KYT3NiqI-X8 --preview-transcript --metadata-analysis
```

#### Enhanced Downloads
```bash
# High-quality download with all transcript formats
python -m my_project https://www.youtube.com/watch?v=KYT3NiqI-X8 --audio --video --transcript --transcript-formats clean timestamped structured --quality 720p

# LLM analysis workflow
python -m my_project https://www.youtube.com/watch?v=KYT3NiqI-X8 --transcript --transcript-formats clean structured --metadata-analysis --metadata-export json --outdir ./llm_content

# Multi-language content processing
python -m my_project https://www.youtube.com/watch?v=KYT3NiqI-X8 --transcript --lang pt-BR --metadata-analysis --metadata-export markdown
```

#### Batch Processing
```bash
# Process multiple URLs from file
echo "https://www.youtube.com/watch?v=KYT3NiqI-X8" > urls.txt
echo "https://www.youtube.com/watch?v=dQw4w9WgXcQ" >> urls.txt
python -m my_project --batch-file urls.txt --transcript --metadata-export csv
```

## 📁 Output & File Organization

### Enhanced File Structure
```
output_directory/
├── audio/
│   └── video_title.mp3                    # High-quality audio (192kbps)
├── video/  
│   └── video_title.mp4                    # Original quality video
├── transcripts/
│   ├── video_id_en_clean.txt             # Cleaned text for LLM processing
│   ├── video_id_en_timestamped.txt       # Timestamped for reference
│   └── video_id_en_structured.json       # Complete structured data
└── metadata/
    ├── video_id_metadata.json            # Comprehensive metadata
    ├── video_id_analysis.csv             # Content analysis summary
    └── video_id_report.md                # Human-readable report
```

### Transcript Format Options

#### Clean Format (`_clean.txt`)
- **Purpose**: Optimized for LLM analysis
- **Features**: Filler words removed, normalized text, paragraph structure
- **Use Case**: Direct input to AI models, content analysis

#### Timestamped Format (`_timestamped.txt`)
- **Purpose**: Reference and navigation
- **Features**: Precise timestamps, speaker attribution, chapter markers
- **Use Case**: Video editing, citation, manual review

#### Structured Format (`_structured.json`)
- **Purpose**: Machine processing and integration
- **Features**: Complete metadata, quality scores, content analysis
- **Use Case**: Database import, API integration, advanced processing

### Metadata Export Formats

#### JSON Export (`_metadata.json`)
```json
{
  "video_metadata": { "title": "...", "duration": 300, ... },
  "content_analysis": { "topics": [...], "sentiment": 0.8, ... },
  "quality_assessment": { "content_score": 0.92, "llm_suitable": true }
}
```

#### CSV Export (`_analysis.csv`)
- Content metrics, quality scores, and analysis results in tabular format
- Perfect for spreadsheet analysis and data visualization

#### Markdown Report (`_report.md`)
- Human-readable comprehensive analysis report
- Includes content summary, key insights, and quality assessment

## ⚙️ Configuration

### Configuration File (`config/app_config.json`)
The application uses a centralized configuration file for all preferences:

```json
{
  "downloads": {
    "audio": { "quality": "192", "format": "mp3" },
    "video": { "quality": "720p", "format": "mp4" },
    "output_structure": { "organize_by_type": true }
  },
  "transcripts": {
    "processing": {
      "output_formats": ["clean", "timestamped", "structured"],
      "text_cleaning": { "enabled": true, "remove_filler_words": true },
      "chapter_detection": { "enabled": true, "min_silence_gap": 3.0 }
    }
  },
  "metadata_collection": {
    "enabled": true,
    "content_analysis": { "extract_topics": true, "sentiment_analysis": true },
    "quality_assessment": { "content_quality_score": true }
  }
}
```

### Smart Format Selection

#### Audio Selection Algorithm
1. **Quality scoring** based on bitrate and codec
2. **Format compatibility** prioritization  
3. **Fallback chain** for maximum reliability

#### Video Selection Algorithm  
1. **Resolution preference** matching
2. **Codec efficiency** consideration
3. **File size optimization** when appropriate

#### Transcript Processing Intelligence
1. **Language detection** and preference matching
2. **Quality assessment** (manual vs auto-generated)
3. **Content analysis** for optimal processing

## 🧪 Testing & Development

### Running Tests
```bash
# Install test dependencies
pip install -e ".[test]"

# Run all tests with coverage
python run_tests.py all

# Run specific test categories
python run_tests.py unit        # Fast unit tests
python run_tests.py integration # End-to-end workflows
python run_tests.py network     # Network-dependent tests

# Development workflow
python run_tests.py fast        # Exclude slow tests for rapid iteration
```

### Test Coverage
- **27 comprehensive test cases** covering core functionality
- **Unit tests** for individual components (video processing, transcript handling)
- **Integration tests** for CLI workflows and batch processing
- **Mock testing** for external API dependencies

## 🔧 Troubleshooting

### Common Issues & Solutions

#### Download Issues
- **"No formats found"**: Video may be private, deleted, or region-locked
- **"Network error"**: Check internet connection and try again with retry
- **"Rate limited"**: Wait a few minutes before retrying

#### Transcript Issues  
- **"Transcripts disabled"**: Video owner has disabled captions
- **"Language not available"**: Try auto-generated transcripts or different language
- **"Processing failed"**: Check transcript quality and try basic format only

#### Quality & Performance
- **Poor transcript quality**: Video may have auto-generated captions only
- **Slow processing**: Large videos with extensive metadata analysis take longer
- **Large file sizes**: Use quality preferences to control output size

### Validation Commands
```bash
# Test basic functionality
python -m my_project https://www.youtube.com/watch?v=KYT3NiqI-X8 --info-only

# Test enhanced features
python -m my_project https://www.youtube.com/watch?v=KYT3NiqI-X8 --preview-transcript --metadata-analysis

# Test complete workflow
python -m my_project https://www.youtube.com/watch?v=KYT3NiqI-X8 --audio --transcript --metadata-export json --outdir ./test_output
```

## 🚀 Development Status

### Current Release: v1.0 - Production Ready
- ✅ **Core functionality** stable and tested
- ✅ **Enhanced transcript processing** with multiple output formats
- ✅ **Comprehensive metadata analysis** and export capabilities
- ✅ **Professional testing framework** with 90%+ coverage
- ✅ **LLM-ready exports** for AI analysis workflows

### Planned Enhancements
- **Enhancement #3**: Smart content organization and batch processing
- **Database integration**: Content management and duplicate detection
- **Web interface**: Django-based interactive mode
- **Advanced analytics**: Topic clustering and content insights
- **Performance optimization**: Parallel processing and caching

## 📋 Requirements

### System Requirements
- **Python 3.10+** (tested on 3.10, 3.11, 3.12)
- **Windows/Linux/macOS** cross-platform compatibility
- **Internet connection** for YouTube access

### Dependencies
```bash
# Core dependencies (auto-installed)
yt-dlp>=2023.7.6              # YouTube download engine
youtube-transcript-api>=0.6.0  # Transcript extraction  
colorama>=0.4.6               # Cross-platform colored output

# Optional testing dependencies
pytest>=7.4.0                # Testing framework
pytest-cov>=4.1.0            # Coverage reporting
```

## 📄 License

MIT License - See LICENSE file for details

## 🤝 Contributing

1. **Fork the repository**
2. **Create feature branch** (`git checkout -b feature/amazing-feature`)
3. **Run tests** (`python run_tests.py all`)
4. **Commit changes** (`git commit -m 'Add amazing feature'`)
5. **Push to branch** (`git push origin feature/amazing-feature`)
6. **Open Pull Request**

### Development Guidelines
- Maintain test coverage above 90%
- Follow existing code structure and patterns
- Update documentation for new features
- Ensure cross-platform compatibility

---

**Created for efficient YouTube content processing and LLM analysis workflows.**