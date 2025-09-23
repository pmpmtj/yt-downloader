"""
transcript_processor.py

Enhanced transcript processing and formatting for LLM analysis.
Handles text cleaning, multiple output formats, and chapter detection.
"""

import json
import re
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

# Import logging
try:
    from .logger_utils.logger_utils import setup_logger
    from .utils.path_utils import load_config
except ImportError:
    from logger_utils.logger_utils import setup_logger
    # For standalone operation, we'll use a simple config
    def load_config():
        return {
            "transcripts": {
                "processing": {
                    "output_formats": {
                        "clean": True,
                        "timestamped": True,
                        "structured": True
                    },
                    "text_cleaning": {
                        "enabled": True,
                        "remove_filler_words": True,
                        "normalize_whitespace": True,
                        "fix_transcription_artifacts": True,
                        "filler_words": ["um", "uh", "like", "you know", "so", "well", "actually", "basically", "literally"]
                    },
                    "chapter_detection": {
                        "enabled": True,
                        "min_silence_gap_seconds": 3.0,
                        "min_chapter_length_seconds": 30.0,
                        "include_chapter_summaries": True
                    },
                    "preview": {
                        "max_lines": 10,
                        "include_stats": True,
                        "include_quality_indicators": True
                    }
                }
            },
            "metadata_collection": {
                "enabled": False  # Disable for standalone operation
            }
        }

# Setup logger for this module
logger = setup_logger("transcript_processor")


class TranscriptProcessor:
    """Processes and formats YouTube transcripts for various use cases."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize processor with configuration."""
        if config is None:
            try:
                config = load_config()
            except Exception as e:
                logger.warning(f"Could not load config, using defaults: {e}")
                config = {}
        
        self.config = config.get("transcripts", {}).get("processing", {})
        self.text_cleaning_config = self.config.get("text_cleaning", {})
        self.chapter_config = self.config.get("chapter_detection", {})
        self.preview_config = self.config.get("preview", {})
        
        logger.debug(f"TranscriptProcessor initialized with config: {self.config}")
    
    def clean_text(self, text: str) -> str:
        """Clean transcript text for better LLM consumption."""
        if not self.text_cleaning_config.get("enabled", True):
            return text
        
        logger.debug("Starting text cleaning process")
        cleaned = text
        
        # Remove filler words if enabled
        if self.text_cleaning_config.get("remove_filler_words", True):
            filler_words = self.text_cleaning_config.get("filler_words", [])
            if filler_words:
                # Create pattern for filler words (case insensitive, word boundaries)
                pattern = r'\b(?:' + '|'.join(re.escape(word) for word in filler_words) + r')\b'
                cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
                logger.debug(f"Removed filler words: {len(filler_words)} patterns")
        
        # Normalize whitespace if enabled
        if self.text_cleaning_config.get("normalize_whitespace", True):
            # Replace multiple spaces with single space
            cleaned = re.sub(r'\s+', ' ', cleaned)
            # Remove leading/trailing whitespace from lines
            cleaned = '\n'.join(line.strip() for line in cleaned.split('\n'))
            logger.debug("Normalized whitespace")
        
        # Fix transcription artifacts if enabled
        if self.text_cleaning_config.get("fix_transcription_artifacts", True):
            # Remove repeated words (like "the the" -> "the")
            cleaned = re.sub(r'\b(\w+)\s+\1\b', r'\1', cleaned, flags=re.IGNORECASE)
            # Fix common transcription errors
            cleaned = re.sub(r'\b(\w+)\s*-\s*\1\b', r'\1', cleaned)  # "word - word" -> "word"
            logger.debug("Fixed transcription artifacts")
        
        # Final cleanup
        cleaned = cleaned.strip()
        logger.debug(f"Text cleaning complete. Original length: {len(text)}, Cleaned length: {len(cleaned)}")
        
        return cleaned
    
    def detect_chapters(self, transcript_entries: List[Dict]) -> List[Dict[str, Any]]:
        """Detect natural chapters in transcript based on timestamp gaps."""
        if not self.chapter_config.get("enabled", True):
            return []
        
        logger.debug("Starting chapter detection")
        min_gap = self.chapter_config.get("min_silence_gap_seconds", 3.0)
        min_length = self.chapter_config.get("min_chapter_length_seconds", 30.0)
        include_summaries = self.chapter_config.get("include_chapter_summaries", True)
        
        chapters = []
        current_chapter_start = 0
        current_chapter_text = []
        
        for i, entry in enumerate(transcript_entries):
            # Handle both dict and object formats
            try:
                start_time = float(entry.get('start', 0) if isinstance(entry, dict) else getattr(entry, 'start', 0))
                text = entry.get('text', '') if isinstance(entry, dict) else getattr(entry, 'text', '')
            except (ValueError, AttributeError):
                continue
            
            current_chapter_text.append(text)
            
            # Check if this is a chapter break
            is_chapter_break = False
            if i < len(transcript_entries) - 1:
                try:
                    next_entry = transcript_entries[i + 1]
                    next_start = float(next_entry.get('start', 0) if isinstance(next_entry, dict) else getattr(next_entry, 'start', 0))
                    gap = next_start - start_time
                    
                    if gap >= min_gap and start_time - current_chapter_start >= min_length:
                        is_chapter_break = True
                except (ValueError, AttributeError):
                    pass
            
            # End of transcript is always a chapter break
            if i == len(transcript_entries) - 1:
                is_chapter_break = True
            
            if is_chapter_break and start_time - current_chapter_start >= min_length:
                chapter_text = ' '.join(current_chapter_text).strip()
                
                # Create chapter summary (first few words)
                summary = ""
                if include_summaries and chapter_text:
                    words = chapter_text.split()[:8]  # First 8 words
                    summary = ' '.join(words) + ('...' if len(words) == 8 else '')
                
                chapters.append({
                    'start_time': current_chapter_start,
                    'end_time': start_time,
                    'duration': start_time - current_chapter_start,
                    'text': chapter_text,
                    'summary': summary,
                    'word_count': len(chapter_text.split())
                })
                
                logger.debug(f"Chapter detected: {current_chapter_start:.1f}s-{start_time:.1f}s ({len(chapter_text)} chars)")
                
                # Start new chapter
                current_chapter_start = start_time
                current_chapter_text = []
        
        logger.info(f"Chapter detection complete: {len(chapters)} chapters found")
        return chapters
    
    def generate_clean_transcript(self, transcript_entries: List[Dict]) -> str:
        """Generate clean text transcript optimized for LLM analysis."""
        logger.debug("Generating clean transcript format")
        
        # Extract text content
        text_parts = []
        for entry in transcript_entries:
            try:
                text = entry.get('text', '') if isinstance(entry, dict) else getattr(entry, 'text', '')
                if text.strip():
                    text_parts.append(text.strip())
            except AttributeError:
                continue
        
        # Join and clean
        raw_text = ' '.join(text_parts)
        clean_text = self.clean_text(raw_text)
        
        logger.debug(f"Clean transcript generated: {len(clean_text)} characters")
        return clean_text
    
    def generate_timestamped_transcript(self, transcript_entries: List[Dict]) -> str:
        """Generate timestamped transcript (original format)."""
        logger.debug("Generating timestamped transcript format")
        
        lines = []
        for entry in transcript_entries:
            try:
                start = entry.get('start') if isinstance(entry, dict) else getattr(entry, 'start', None)
                text = entry.get('text', '') if isinstance(entry, dict) else getattr(entry, 'text', '')
                
                if start is not None and text.strip():
                    start_val = float(start)
                    lines.append(f"[{start_val:.2f}s] {text.strip()}")
            except (ValueError, AttributeError):
                continue
        
        result = '\n'.join(lines)
        logger.debug(f"Timestamped transcript generated: {len(lines)} lines")
        return result
    
    def generate_structured_transcript(self, transcript_entries: List[Dict], video_metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate structured JSON transcript with metadata."""
        logger.debug("Generating structured transcript format")
        
        if video_metadata is None:
            video_metadata = {}
        
        # Generate chapters
        chapters = self.detect_chapters(transcript_entries)
        
        # Calculate basic statistics
        total_text = ' '.join([
            (entry.get('text', '') if isinstance(entry, dict) else getattr(entry, 'text', ''))
            for entry in transcript_entries
        ])
        
        word_count = len(total_text.split())
        char_count = len(total_text)
        estimated_reading_time = word_count / 200  # ~200 words per minute
        
        # Build basic structured data
        structured = {
            'metadata': {
                'video_id': video_metadata.get('id', ''),
                'title': video_metadata.get('title', ''),
                'duration': video_metadata.get('duration', 0),
                'upload_date': video_metadata.get('upload_date', ''),
                'uploader': video_metadata.get('uploader', ''),
                'processed_at': None,  # Will be set when saving
                'processor_version': '1.0'
            },
            'statistics': {
                'total_entries': len(transcript_entries),
                'word_count': word_count,
                'character_count': char_count,
                'estimated_reading_time_minutes': round(estimated_reading_time, 1),
                'chapters_detected': len(chapters)
            },
            'transcript': {
                'entries': transcript_entries,
                'chapters': chapters
            },
            'formats': {
                'clean_text': self.generate_clean_transcript(transcript_entries),
                'timestamped_text': self.generate_timestamped_transcript(transcript_entries)
            }
        }
        
        # 🆕 Add comprehensive metadata collection if enabled
        try:
            config = load_config()
            
            if config.get("metadata_collection", {}).get("enabled", False):  # Disabled for now
                try:
                    from .metadata_collector import collect_comprehensive_metadata
                except ImportError:
                    from metadata_collector import collect_comprehensive_metadata
                
                logger.debug("Adding comprehensive metadata to structured transcript")
                comprehensive_metadata = collect_comprehensive_metadata(video_metadata, transcript_entries, config)
                
                # Integrate metadata into structured format
                structured['comprehensive_metadata'] = comprehensive_metadata
                
                # Enhance basic statistics with advanced metrics
                if comprehensive_metadata.get('transcript_analysis', {}).get('content_metrics'):
                    advanced_metrics = comprehensive_metadata['transcript_analysis']['content_metrics']
                    structured['statistics'].update({
                        'speaking_rate_wpm': advanced_metrics.get('speaking_rate_wpm', 0),
                        'lexical_diversity': advanced_metrics.get('lexical_diversity', 0),
                        'average_words_per_sentence': advanced_metrics.get('average_words_per_sentence', 0)
                    })
                
                # Add content summary for quick reference
                if comprehensive_metadata.get('content_summary'):
                    structured['content_summary'] = comprehensive_metadata['content_summary']
                
                logger.debug("Enhanced structured transcript with comprehensive metadata")
                
        except Exception as e:
            logger.warning(f"Could not add comprehensive metadata: {e}")
            # Continue without comprehensive metadata - basic structure is still useful
        
        logger.debug(f"Structured transcript generated: {word_count} words, {len(chapters)} chapters")
        return structured
    
    def generate_preview(self, transcript_entries: List[Dict], video_metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate preview information for transcript."""
        logger.debug("Generating transcript preview")
        
        max_lines = self.preview_config.get("max_lines", 10)
        include_stats = self.preview_config.get("include_stats", True)
        include_quality = self.preview_config.get("include_quality_indicators", True)
        
        # Get first few lines for preview
        preview_lines = []
        for i, entry in enumerate(transcript_entries[:max_lines]):
            try:
                start = entry.get('start') if isinstance(entry, dict) else getattr(entry, 'start', None)
                text = entry.get('text', '') if isinstance(entry, dict) else getattr(entry, 'text', '')
                
                if start is not None and text.strip():
                    start_val = float(start)
                    preview_lines.append(f"[{start_val:.2f}s] {text.strip()}")
            except (ValueError, AttributeError):
                continue
        
        preview_text = '\n'.join(preview_lines)
        if len(transcript_entries) > max_lines:
            preview_text += f"\n... ({len(transcript_entries) - max_lines} more entries)"
        
        preview_data = {
            'preview_text': preview_text,
            'total_entries': len(transcript_entries)
        }
        
        # Add statistics if requested
        if include_stats:
            total_text = ' '.join([
                (entry.get('text', '') if isinstance(entry, dict) else getattr(entry, 'text', ''))
                for entry in transcript_entries
            ])
            word_count = len(total_text.split())
            estimated_reading_time = word_count / 200
            
            preview_data['statistics'] = {
                'word_count': word_count,
                'character_count': len(total_text),
                'estimated_reading_time_minutes': round(estimated_reading_time, 1)
            }
        
        # Add quality indicators if requested
        if include_quality:
            # Simple quality heuristics
            avg_entry_length = sum(len(entry.get('text', '') if isinstance(entry, dict) else getattr(entry, 'text', '')) 
                                 for entry in transcript_entries) / len(transcript_entries) if transcript_entries else 0
            
            quality_score = "High" if avg_entry_length > 50 else "Medium" if avg_entry_length > 20 else "Low"
            
            preview_data['quality_indicators'] = {
                'average_entry_length': round(avg_entry_length, 1),
                'quality_estimate': quality_score,
                'has_timestamps': len(preview_lines) > 0
            }
        
        logger.debug(f"Preview generated: {len(preview_lines)} lines shown")
        return preview_data


def process_transcript_data(transcript_entries: List[Dict], video_metadata: Dict[str, Any] = None, 
                          formats: List[str] = None, config: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Process transcript data and return multiple formats.
    
    Args:
        transcript_entries: Raw transcript entries from YouTube API
        video_metadata: Video metadata dictionary
        formats: List of formats to generate ('clean', 'timestamped', 'structured')
        config: Configuration dictionary
    
    Returns:
        Dictionary with generated formats and metadata
    """
    logger.info("Starting transcript processing")
    
    if formats is None:
        formats = ['clean', 'timestamped', 'structured']
    
    processor = TranscriptProcessor(config)
    results = {}
    
    if 'clean' in formats:
        results['clean'] = processor.generate_clean_transcript(transcript_entries)
        logger.debug("Generated clean format")
    
    if 'timestamped' in formats:
        results['timestamped'] = processor.generate_timestamped_transcript(transcript_entries)
        logger.debug("Generated timestamped format")
    
    if 'structured' in formats:
        results['structured'] = processor.generate_structured_transcript(transcript_entries, video_metadata)
        logger.debug("Generated structured format")
    
    logger.info(f"Transcript processing complete: {len(formats)} formats generated")
    return results
