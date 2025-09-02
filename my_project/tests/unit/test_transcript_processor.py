#!/usr/bin/env python3
"""
test_transcript_processor.py

Unit tests for transcript_processor module.
Tests text cleaning, format generation, and transcript processing functionality.
"""

import pytest
from unittest.mock import Mock, patch
import json
from datetime import datetime

from src.my_project.transcript_processor import TranscriptProcessor


class TestTranscriptProcessor:
    """Test TranscriptProcessor class functionality."""
    
    def setup_method(self):
        """Set up test fixtures for each test method."""
        self.config = {
            "text_processing": {
                "remove_filler_words": True,
                "normalize_whitespace": True,
                "fix_transcription_artifacts": True
            },
            "chapter_detection": {
                "enabled": True,
                "min_chapter_length": 30,
                "silence_gap_threshold": 3.0
            }
        }
        self.processor = TranscriptProcessor(self.config)
        
        self.sample_transcript = [
            {'text': 'Hello everyone', 'start': 0.0, 'duration': 2.0},
            {'text': 'um, welcome to my channel', 'start': 2.0, 'duration': 3.0},
            {'text': 'today we will, uh, learn about', 'start': 5.0, 'duration': 4.0},
            {'text': 'artificial intelligence', 'start': 9.0, 'duration': 3.0},
            {'text': '[Music]', 'start': 12.0, 'duration': 5.0},
            {'text': 'so let\'s get started', 'start': 17.0, 'duration': 3.0}
        ]
        
        self.sample_video_metadata = {
            'basic_info': {
                'title': 'AI Tutorial',
                'uploader': 'Tech Channel',
                'duration_seconds': 720,
                'video_id': 'test123'
            }
        }
    
    def test_transcript_processor_initialization(self):
        """Test TranscriptProcessor initialization."""
        processor = TranscriptProcessor()
        assert processor is not None
        
        # Test with config
        processor_with_config = TranscriptProcessor(self.config)
        assert processor_with_config.config == self.config
    
    @pytest.mark.unit
    def test_clean_transcript_text_basic(self):
        """Test basic text cleaning functionality."""
        dirty_text = "Hello um, everyone. This is, uh, a test."
        
        cleaned = self.processor._clean_transcript_text(dirty_text)
        
        assert 'um,' not in cleaned
        assert 'uh,' not in cleaned
        assert 'Hello everyone' in cleaned
        assert 'This is a test' in cleaned
    
    @pytest.mark.unit
    def test_clean_transcript_text_artifacts(self):
        """Test removal of transcription artifacts."""
        text_with_artifacts = "Hello [Music] everyone [Applause] welcome [Laughter] here"
        
        cleaned = self.processor._clean_transcript_text(text_with_artifacts)
        
        assert '[Music]' not in cleaned
        assert '[Applause]' not in cleaned
        assert '[Laughter]' not in cleaned
        assert 'Hello everyone welcome here' in cleaned
    
    @pytest.mark.unit
    def test_clean_transcript_text_whitespace(self):
        """Test whitespace normalization."""
        text_with_spaces = "Hello    everyone\t\twelcome\n\nhere"
        
        cleaned = self.processor._clean_transcript_text(text_with_spaces)
        
        assert '    ' not in cleaned
        assert '\t\t' not in cleaned
        assert '\n\n' not in cleaned
        assert 'Hello everyone welcome here' in cleaned
    
    @pytest.mark.unit
    def test_detect_chapters_by_silence(self):
        """Test chapter detection based on silence gaps."""
        transcript_with_gaps = [
            {'text': 'Introduction part', 'start': 0.0, 'duration': 2.0},
            {'text': 'more intro', 'start': 2.0, 'duration': 3.0},
            # Large gap here (5 seconds)
            {'text': 'Chapter 2 starts', 'start': 10.0, 'duration': 3.0},
            {'text': 'chapter 2 content', 'start': 13.0, 'duration': 4.0},
            # Another large gap (6 seconds)
            {'text': 'Chapter 3 begins', 'start': 23.0, 'duration': 3.0}
        ]
        
        chapters = self.processor._detect_chapters(transcript_with_gaps)
        
        assert len(chapters) >= 2  # Should detect chapter breaks
        assert chapters[0]['start_time'] == 0.0
        assert any(chapter['start_time'] >= 10.0 for chapter in chapters)
    
    @pytest.mark.unit
    def test_detect_chapters_min_length(self):
        """Test chapter detection respects minimum length."""
        short_transcript = [
            {'text': 'Very short', 'start': 0.0, 'duration': 1.0},
            {'text': 'content here', 'start': 10.0, 'duration': 1.0}
        ]
        
        chapters = self.processor._detect_chapters(short_transcript)
        
        # Should not create chapters for very short content
        assert len(chapters) <= 1
    
    @pytest.mark.unit
    def test_generate_clean_transcript(self):
        """Test clean transcript generation."""
        clean_transcript = self.processor.generate_clean_transcript(self.sample_transcript)
        
        assert isinstance(clean_transcript, str)
        assert 'um,' not in clean_transcript.lower()
        assert 'uh,' not in clean_transcript.lower()
        assert '[Music]' not in clean_transcript
        assert 'Hello everyone' in clean_transcript
        assert 'artificial intelligence' in clean_transcript
    
    @pytest.mark.unit
    def test_generate_timestamped_transcript(self):
        """Test timestamped transcript generation."""
        timestamped = self.processor.generate_timestamped_transcript(self.sample_transcript)
        
        assert isinstance(timestamped, str)
        assert '[00:00:00]' in timestamped  # Should have timestamps
        assert 'Hello everyone' in timestamped
        assert '[00:00:02]' in timestamped or '[0:02]' in timestamped
    
    @pytest.mark.unit
    def test_generate_structured_transcript(self):
        """Test structured transcript generation."""
        structured = self.processor.generate_structured_transcript(
            self.sample_transcript, 
            self.sample_video_metadata
        )
        
        assert isinstance(structured, dict)
        assert 'metadata' in structured
        assert 'entries' in structured
        assert 'statistics' in structured
        assert 'formats' in structured
        
        # Check metadata
        assert structured['metadata']['title'] == 'AI Tutorial'
        assert structured['metadata']['uploader'] == 'Tech Channel'
        
        # Check entries
        assert len(structured['entries']) == len(self.sample_transcript)
        assert structured['entries'][0]['text'] == 'Hello everyone'
        assert structured['entries'][0]['start'] == 0.0
        
        # Check statistics
        stats = structured['statistics']
        assert 'total_entries' in stats
        assert 'total_duration' in stats
        assert 'word_count' in stats
        assert stats['total_entries'] == len(self.sample_transcript)
    
    @pytest.mark.unit
    def test_generate_structured_transcript_with_chapters(self):
        """Test structured transcript includes chapter detection."""
        # Create transcript that should have detectable chapters
        long_transcript = [
            {'text': f'Entry {i}', 'start': float(i * 2), 'duration': 2.0}
            for i in range(20)
        ]
        # Add a big gap
        long_transcript.append({'text': 'New chapter', 'start': 60.0, 'duration': 2.0})
        
        structured = self.processor.generate_structured_transcript(long_transcript, self.sample_video_metadata)
        
        assert 'chapters' in structured
        chapters = structured['chapters']
        assert len(chapters) >= 1
        assert chapters[0]['start_time'] == 0.0
    
    @pytest.mark.unit
    @patch('src.my_project.transcript_processor.collect_comprehensive_metadata')
    def test_generate_structured_transcript_with_metadata_analysis(self, mock_collect_metadata):
        """Test structured transcript includes comprehensive metadata when enabled."""
        mock_metadata = {
            'transcript_analysis': {
                'content_metrics': {'speaking_rate_wpm': 150, 'lexical_diversity': 0.8}
            },
            'content_summary': {'overview': {'title': 'Test'}}
        }
        mock_collect_metadata.return_value = mock_metadata
        
        # Enable metadata collection
        with patch('src.my_project.transcript_processor.load_config') as mock_load_config:
            mock_load_config.return_value = {"metadata_collection": {"enabled": True}}
            
            structured = self.processor.generate_structured_transcript(
                self.sample_transcript, 
                self.sample_video_metadata
            )
        
        assert 'comprehensive_metadata' in structured
        assert structured['comprehensive_metadata'] == mock_metadata
        
        # Check that advanced metrics were added to statistics
        stats = structured['statistics']
        assert 'speaking_rate_wpm' in stats
        assert 'lexical_diversity' in stats
        assert stats['speaking_rate_wpm'] == 150
    
    @pytest.mark.unit
    def test_format_timestamp(self):
        """Test timestamp formatting."""
        # Test various timestamp formats
        assert self.processor._format_timestamp(0.0) == '[00:00:00]'
        assert self.processor._format_timestamp(65.0) == '[00:01:05]'
        assert self.processor._format_timestamp(3661.5) == '[01:01:01]'
    
    @pytest.mark.unit
    def test_calculate_statistics(self):
        """Test statistics calculation."""
        stats = self.processor._calculate_statistics(self.sample_transcript)
        
        assert 'total_entries' in stats
        assert 'total_duration' in stats
        assert 'word_count' in stats
        assert 'average_words_per_entry' in stats
        
        assert stats['total_entries'] == len(self.sample_transcript)
        assert stats['word_count'] > 0
        assert stats['total_duration'] > 0
    
    @pytest.mark.unit
    def test_remove_filler_words(self):
        """Test filler word removal."""
        text_with_fillers = "So um, like, you know, this is, uh, really good, right?"
        
        cleaned = self.processor._remove_filler_words(text_with_fillers)
        
        assert 'um,' not in cleaned
        assert 'like,' not in cleaned
        assert 'you know,' not in cleaned
        assert 'uh,' not in cleaned
        assert 'So this is really good, right?' in cleaned
    
    @pytest.mark.unit
    def test_fix_transcription_artifacts(self):
        """Test transcription artifact fixing."""
        text_with_artifacts = "Hello [Music] world [Applause] [Laughter] [Background noise]"
        
        fixed = self.processor._fix_transcription_artifacts(text_with_artifacts)
        
        assert '[Music]' not in fixed
        assert '[Applause]' not in fixed
        assert '[Laughter]' not in fixed
        assert '[Background noise]' not in fixed
        assert 'Hello world' in fixed
    
    @pytest.mark.unit
    def test_normalize_whitespace(self):
        """Test whitespace normalization."""
        messy_text = "Hello\t\tworld\n\n\nthis   is    messy     text"
        
        normalized = self.processor._normalize_whitespace(messy_text)
        
        assert normalized == "Hello world this is messy text"


class TestTranscriptProcessorEdgeCases:
    """Test edge cases and error conditions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.processor = TranscriptProcessor()
    
    @pytest.mark.unit
    def test_empty_transcript_handling(self):
        """Test handling of empty transcript."""
        empty_transcript = []
        
        clean = self.processor.generate_clean_transcript(empty_transcript)
        timestamped = self.processor.generate_timestamped_transcript(empty_transcript)
        structured = self.processor.generate_structured_transcript(empty_transcript, {})
        
        assert clean == ""
        assert timestamped == ""
        assert isinstance(structured, dict)
        assert structured['statistics']['total_entries'] == 0
    
    @pytest.mark.unit
    def test_malformed_transcript_entries(self):
        """Test handling of malformed transcript entries."""
        malformed_transcript = [
            {'text': 'Good entry', 'start': 0.0, 'duration': 2.0},
            {'text': None, 'start': 2.0, 'duration': 1.0},  # None text
            {'start': 3.0, 'duration': 1.0},  # Missing text
            {'text': 'Another good entry', 'start': 4.0, 'duration': 2.0}
        ]
        
        clean = self.processor.generate_clean_transcript(malformed_transcript)
        
        assert 'Good entry' in clean
        assert 'Another good entry' in clean
        # Should handle malformed entries gracefully without crashing
        assert isinstance(clean, str)
    
    @pytest.mark.unit
    def test_transcript_with_negative_timestamps(self):
        """Test handling of negative timestamps."""
        transcript_with_negatives = [
            {'text': 'Before start', 'start': -1.0, 'duration': 1.0},
            {'text': 'Normal entry', 'start': 0.0, 'duration': 2.0}
        ]
        
        structured = self.processor.generate_structured_transcript(transcript_with_negatives, {})
        
        # Should handle gracefully
        assert isinstance(structured, dict)
        assert len(structured['entries']) == 2
    
    @pytest.mark.unit
    def test_very_long_transcript(self):
        """Test handling of very long transcripts."""
        # Create a very long transcript
        long_transcript = [
            {'text': f'Entry number {i}', 'start': float(i), 'duration': 1.0}
            for i in range(1000)
        ]
        
        clean = self.processor.generate_clean_transcript(long_transcript)
        
        assert isinstance(clean, str)
        assert len(clean) > 1000  # Should process all entries
        assert 'Entry number 0' in clean
        assert 'Entry number 999' in clean
    
    @pytest.mark.unit
    def test_transcript_with_unicode_characters(self):
        """Test handling of unicode characters in transcript."""
        unicode_transcript = [
            {'text': 'Hello 世界', 'start': 0.0, 'duration': 2.0},
            {'text': 'café résumé naïve', 'start': 2.0, 'duration': 3.0},
            {'text': '🎵 music emoji 🎵', 'start': 5.0, 'duration': 2.0}
        ]
        
        clean = self.processor.generate_clean_transcript(unicode_transcript)
        structured = self.processor.generate_structured_transcript(unicode_transcript, {})
        
        assert '世界' in clean
        assert 'café résumé naïve' in clean
        assert '🎵' in clean
        assert isinstance(structured, dict)
    
    @pytest.mark.unit
    def test_config_loading_failure(self):
        """Test graceful handling of config loading failure."""
        with patch('src.my_project.transcript_processor.load_config') as mock_load_config:
            mock_load_config.side_effect = Exception("Config load failed")
            
            # Should not crash, should use defaults
            processor = TranscriptProcessor()
            
            result = processor.generate_clean_transcript([
                {'text': 'Test text', 'start': 0.0, 'duration': 1.0}
            ])
            
            assert isinstance(result, str)
            assert 'Test text' in result


# Removed TestProcessTranscriptDataFunction as that function doesn't exist as a standalone
# All transcript processing is handled via the TranscriptProcessor class methods
