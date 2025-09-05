#!/usr/bin/env python3
"""
test_metadata_collector.py

Unit tests for metadata_collector module.
Tests content analysis, quality assessment, and metadata collection functionality.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from src.my_project.metadata_collector import MetadataCollector, collect_comprehensive_metadata


class TestMetadataCollector:
    """Test MetadataCollector class functionality."""
    
    def setup_method(self):
        """Set up test fixtures for each test method."""
        self.config = {
            "metadata_collection": {
                "content_analysis": {
                    "extract_keywords": True,
                    "extract_topics": True,
                    "detect_language": True,
                    "content_categorization": True
                },
                "video_metadata": {
                    "technical_details": True,
                    "engagement_metrics": True,
                    "channel_info": True,
                    "detailed_description": True
                },
                "quality_assessment": {
                    "content_quality_score": True
                }
            }
        }
        self.collector = MetadataCollector(self.config)
        
        self.sample_video_info = {
            'id': 'test123',
            'title': 'Introduction to Machine Learning',
            'uploader': 'Tech Education Channel',
            'uploader_id': 'tech_edu_123',
            'upload_date': '20240101',
            'duration': 1800,  # 30 minutes
            'view_count': 50000,
            'like_count': 2000,
            'comment_count': 150,
            'webpage_url': 'https://youtube.com/watch?v=test123',
            'description': 'This is a comprehensive tutorial about machine learning basics. We will cover supervised learning, unsupervised learning, and neural networks.',
            'tags': ['machine learning', 'AI', 'tutorial', 'education'],
            'categories': ['Education'],
            'fps': 30,
            'aspect_ratio': 1.78,
            'formats': [
                {
                    'format_id': '140',
                    'ext': 'm4a',
                    'vcodec': 'none',
                    'acodec': 'mp4a.40.2',
                    'filesize': 5000000,
                    'height': None
                },
                {
                    'format_id': '22',
                    'ext': 'mp4', 
                    'vcodec': 'avc1.64001F',
                    'acodec': 'mp4a.40.2',
                    'filesize': 50000000,
                    'height': 720
                }
            ],
            'channel': 'Tech Education Channel',
            'channel_id': 'UC123456789',
            'thumbnails': [
                {'url': 'https://example.com/thumb1.jpg'},
                {'url': 'https://example.com/thumb2.jpg'}
            ]
        }
        
        self.sample_transcript = [
            {'text': 'Hello everyone, welcome to this machine learning tutorial', 'start': 0.0, 'duration': 4.0},
            {'text': 'Today we will learn about supervised learning algorithms', 'start': 4.0, 'duration': 4.0},
            {'text': 'Neural networks are a powerful tool for pattern recognition', 'start': 8.0, 'duration': 5.0},
            {'text': 'Let us start with linear regression', 'start': 13.0, 'duration': 3.0}
        ]
    
    def test_metadata_collector_initialization(self):
        """Test MetadataCollector initialization."""
        # Test with config
        collector = MetadataCollector(self.config)
        assert collector.config == self.config["metadata_collection"]
        
        # Test without config
        with patch('src.my_project.metadata_collector.load_config') as mock_load:
            mock_load.return_value = {"metadata_collection": {"enabled": True}}
            collector_no_config = MetadataCollector()
            assert collector_no_config.config is not None
    
    @pytest.mark.unit
    def test_extract_video_metadata(self):
        """Test video metadata extraction."""
        metadata = self.collector.extract_video_metadata(self.sample_video_info)
        
        assert isinstance(metadata, dict)
        assert 'basic_info' in metadata
        assert 'technical_details' in metadata
        assert 'engagement_metrics' in metadata
        assert 'channel_info' in metadata
        assert 'content_details' in metadata
        
        # Check basic info
        basic_info = metadata['basic_info']
        assert basic_info['video_id'] == 'test123'
        assert basic_info['title'] == 'Introduction to Machine Learning'
        assert basic_info['uploader'] == 'Tech Education Channel'
        assert basic_info['duration_seconds'] == 1800
    
    @pytest.mark.unit
    def test_extract_video_metadata_none_input(self):
        """Test video metadata extraction with None input."""
        metadata = self.collector.extract_video_metadata(None)
        
        assert isinstance(metadata, dict)
        # Should return empty structure
        assert metadata['basic_info'] == {}
        assert metadata['technical_details'] == {}
    
    @pytest.mark.unit
    def test_extract_basic_info(self):
        """Test basic info extraction."""
        basic_info = self.collector._extract_basic_info(self.sample_video_info)
        
        assert basic_info['video_id'] == 'test123'
        assert basic_info['title'] == 'Introduction to Machine Learning'
        assert basic_info['uploader'] == 'Tech Education Channel'
        assert basic_info['duration_readable'] == '30m 0s'
        assert basic_info['webpage_url'] == 'https://youtube.com/watch?v=test123'
    
    @pytest.mark.unit
    def test_extract_technical_details(self):
        """Test technical details extraction."""
        technical = self.collector._extract_technical_details(self.sample_video_info)
        
        assert technical['max_resolution'] == '720p'
        assert '720p' in technical['available_qualities']
        assert technical['total_formats'] == 2
        assert technical['video_formats_count'] == 1
        assert technical['audio_formats_count'] == 1
        assert 'avc1' in technical['video_codecs'] or 'avc1.64001F' in str(technical['video_codecs'])
        assert technical['fps'] == 30
        assert technical['aspect_ratio'] == 1.78
    
    @pytest.mark.unit
    def test_extract_engagement_metrics(self):
        """Test engagement metrics extraction."""
        engagement = self.collector._extract_engagement_metrics(self.sample_video_info)
        
        assert engagement['view_count'] == 50000
        assert engagement['like_count'] == 2000
        assert engagement['comment_count'] == 150
        assert engagement['engagement_rate_percent'] == 4.0  # 2000/50000 * 100
        assert engagement['days_since_upload'] > 0
        assert engagement['views_per_day'] > 0
    
    @pytest.mark.unit
    def test_extract_channel_info(self):
        """Test channel info extraction."""
        channel_info = self.collector._extract_channel_info(self.sample_video_info)
        
        assert channel_info['channel'] == 'Tech Education Channel'
        assert channel_info['channel_id'] == 'UC123456789'
        assert channel_info['uploader_url'] == ''  # Not provided in sample
    
    @pytest.mark.unit
    def test_extract_content_details(self):
        """Test content details extraction."""
        content_details = self.collector._extract_content_details(self.sample_video_info)
        
        assert 'machine learning' in content_details['description']
        assert content_details['description_length'] > 50
        assert content_details['tags'] == ['machine learning', 'AI', 'tutorial', 'education']
        assert content_details['tag_count'] == 4
        assert content_details['categories'] == ['Education']
        assert content_details['thumbnails_count'] == 2
    
    @pytest.mark.unit
    def test_analyze_transcript_content(self):
        """Test transcript content analysis."""
        video_metadata = self.collector.extract_video_metadata(self.sample_video_info)
        
        analysis = self.collector.analyze_transcript_content(self.sample_transcript, video_metadata)
        
        assert isinstance(analysis, dict)
        assert 'content_metrics' in analysis
        assert 'quality_assessment' in analysis
        assert 'content_analysis' in analysis
        
        # Check content metrics
        metrics = analysis['content_metrics']
        assert metrics['word_count'] > 0
        assert metrics['sentence_count'] > 0
        assert metrics['speaking_rate_wpm'] > 0
        assert metrics['transcript_entries_count'] == len(self.sample_transcript)
    
    @pytest.mark.unit
    def test_analyze_transcript_content_empty(self):
        """Test transcript analysis with empty transcript."""
        analysis = self.collector.analyze_transcript_content([])
        
        assert analysis == {}
    
    @pytest.mark.unit
    def test_calculate_content_metrics(self):
        """Test content metrics calculation."""
        full_text = 'Hello everyone, welcome to this machine learning tutorial. Today we will learn about supervised learning algorithms.'
        
        metrics = self.collector._calculate_content_metrics(full_text, self.sample_transcript)
        
        assert metrics['word_count'] > 0
        assert metrics['sentence_count'] >= 2
        assert metrics['character_count'] > 0
        assert metrics['average_words_per_sentence'] > 0
        assert metrics['lexical_diversity'] > 0
        assert metrics['estimated_reading_time_minutes'] > 0
    
    @pytest.mark.unit
    def test_assess_content_quality(self):
        """Test content quality assessment."""
        clean_text = 'This is a high quality transcript with clear speech and good audio.'
        
        quality = self.collector._assess_content_quality(clean_text, self.sample_transcript)
        
        assert quality['quality_score'] > 0
        assert quality['artifact_count'] >= 0
        assert quality['artifact_ratio'] >= 0
        assert quality['quality_category'] in ['Excellent', 'Very Good', 'Good', 'Fair', 'Poor', 'Very Poor']
        assert quality['average_entry_length'] > 0
    
    @pytest.mark.unit
    def test_assess_content_quality_with_artifacts(self):
        """Test quality assessment with transcription artifacts."""
        dirty_text = 'This is um [Music] a transcript with uh [Applause] many artifacts [Inaudible] and issues.'
        
        quality = self.collector._assess_content_quality(dirty_text, [])
        
        assert quality['artifact_count'] > 0
        assert quality['artifact_ratio'] > 0
        assert quality['quality_score'] < 100  # Should be penalized for artifacts
    
    @pytest.mark.unit
    def test_extract_keywords(self):
        """Test keyword extraction."""
        text = 'machine learning artificial intelligence neural networks deep learning algorithms supervised unsupervised reinforcement learning'
        
        keywords = self.collector._extract_keywords(text, max_keywords=5)
        
        assert isinstance(keywords, list)
        assert len(keywords) <= 5
        for keyword in keywords:
            assert 'keyword' in keyword
            assert 'frequency' in keyword
            assert 'relevance_score' in keyword
        
        # Should find 'learning' as a frequent keyword
        keyword_words = [kw['keyword'] for kw in keywords]
        assert 'learning' in keyword_words
    
    @pytest.mark.unit
    def test_extract_topics(self):
        """Test topic extraction."""
        text = 'Today we will discuss machine learning. This tutorial covers supervised learning algorithms and neural networks.'
        
        topics = self.collector._extract_topics(text)
        
        assert isinstance(topics, list)
        assert len(topics) <= 10
        # Should find capitalized phrases
        if topics:
            for topic in topics:
                assert isinstance(topic, str)
                assert len(topic) > 5
    
    @pytest.mark.unit
    def test_analyze_language(self):
        """Test language analysis."""
        english_text = 'This is a clear English text with common English words and patterns.'
        
        lang_analysis = self.collector._analyze_language(english_text)
        
        assert lang_analysis['detected_language'] == 'English'
        assert lang_analysis['english_probability'] > 0.1
        assert lang_analysis['average_words_per_sentence'] > 0
        assert lang_analysis['complexity_ratio'] >= 0
        assert lang_analysis['readability_level'] in ['Easy', 'Moderate', 'Difficult', 'Very Difficult']
    
    @pytest.mark.unit
    def test_categorize_content(self):
        """Test content categorization."""
        educational_text = 'This tutorial will teach you how to learn machine learning algorithms step by step guide.'
        
        categorization = self.collector._categorize_content(educational_text, self.sample_video_info)
        
        assert categorization['primary_category'] in ['Educational', 'Entertainment', 'News/Documentary', 'Technical', 'General']
        assert isinstance(categorization['category_scores'], dict)
        assert categorization['confidence'] >= 0
        
        # Educational content should score high on educational category
        assert categorization['category_scores']['Educational'] > 0
    
    @pytest.mark.unit
    def test_format_duration(self):
        """Test duration formatting."""
        assert self.collector._format_duration(30) == '30s'
        assert self.collector._format_duration(90) == '1m 30s'
        assert self.collector._format_duration(3661) == '1h 1m 1s'
    
    @pytest.mark.unit
    def test_calculate_days_since_upload(self):
        """Test days since upload calculation."""
        # Test with valid date
        days = self.collector._calculate_days_since_upload('20240101')
        assert days >= 1
        
        # Test with invalid date
        days_invalid = self.collector._calculate_days_since_upload('invalid')
        assert days_invalid == 0
        
        # Test with empty date
        days_empty = self.collector._calculate_days_since_upload('')
        assert days_empty == 0
    
    @pytest.mark.unit
    def test_categorize_quality(self):
        """Test quality categorization."""
        assert self.collector._categorize_quality(95) == 'Excellent'
        assert self.collector._categorize_quality(85) == 'Very Good'
        assert self.collector._categorize_quality(75) == 'Good'
        assert self.collector._categorize_quality(65) == 'Fair'
        assert self.collector._categorize_quality(55) == 'Poor'
        assert self.collector._categorize_quality(45) == 'Very Poor'
    
    @pytest.mark.unit
    def test_assess_readability(self):
        """Test readability assessment."""
        assert self.collector._assess_readability(10, 0.1) == 'Easy'
        assert self.collector._assess_readability(18, 0.25) == 'Moderate'
        assert self.collector._assess_readability(23, 0.35) == 'Difficult'
        assert self.collector._assess_readability(30, 0.5) == 'Very Difficult'
    
    @pytest.mark.unit
    def test_generate_content_summary(self):
        """Test content summary generation."""
        transcript_analysis = self.collector.analyze_transcript_content(self.sample_transcript)
        
        summary = self.collector.generate_content_summary(self.sample_video_info, transcript_analysis)
        
        assert isinstance(summary, dict)
        assert 'overview' in summary
        assert 'content_insights' in summary
        assert 'quality_indicators' in summary
        assert 'llm_suitability' in summary
        
        # Check overview
        overview = summary['overview']
        assert overview['title'] == 'Introduction to Machine Learning'
        assert overview['uploader'] == 'Tech Education Channel'
        assert overview['view_count'] == 50000
    
    @pytest.mark.unit
    def test_generate_content_summary_none_input(self):
        """Test content summary with None video_info."""
        summary = self.collector.generate_content_summary(None, {})
        
        assert isinstance(summary, dict)
        assert summary['overview']['title'] == 'Unknown'
        assert summary['llm_suitability']['recommended_for_llm'] is False
    
    @pytest.mark.unit
    def test_assess_llm_suitability(self):
        """Test LLM suitability assessment."""
        content_metrics = {'word_count': 1500}
        quality_assessment = {'quality_score': 85}
        
        suitability = self.collector._assess_llm_suitability(content_metrics, quality_assessment)
        
        assert isinstance(suitability, dict)
        assert 'overall_score' in suitability
        assert 'length_suitability' in suitability
        assert 'recommended_for_llm' in suitability
        assert 'processing_notes' in suitability
        
        assert suitability['length_suitability'] == 'Ideal Length'
        assert suitability['recommended_for_llm'] is True  # Good word count and quality
    
    @pytest.mark.unit
    def test_generate_processing_notes(self):
        """Test processing notes generation."""
        # High quality content
        good_metrics = {'word_count': 1000, 'speaking_rate_wpm': 150}
        good_quality = {'quality_score': 90, 'artifact_ratio': 0.02}
        
        notes = self.collector._generate_processing_notes(good_metrics, good_quality)
        
        assert isinstance(notes, list)
        assert any('Good quality' in note for note in notes)
        
        # Poor quality content
        poor_metrics = {'word_count': 4000, 'speaking_rate_wpm': 250}
        poor_quality = {'quality_score': 60, 'artifact_ratio': 0.15}
        
        poor_notes = self.collector._generate_processing_notes(poor_metrics, poor_quality)
        
        assert len(poor_notes) > 1  # Should have multiple warnings


class TestCollectComprehensiveMetadata:
    """Test the standalone collect_comprehensive_metadata function."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.sample_video_info = {
            'id': 'test123',
            'title': 'Test Video',
            'uploader': 'Test Channel',
            'duration': 300,
            'upload_date': '20240101'
        }
        
        self.sample_transcript = [
            {'text': 'Hello world', 'start': 0.0, 'duration': 2.0}
        ]
    
    @pytest.mark.unit
    @patch('src.my_project.metadata_collector.datetime')
    def test_collect_comprehensive_metadata_success(self, mock_datetime):
        """Test successful comprehensive metadata collection."""
        mock_datetime.now.return_value.isoformat.return_value = '2024-01-01T12:00:00'
        
        config = {"metadata_collection": {"enabled": True}}
        
        result = collect_comprehensive_metadata(self.sample_video_info, self.sample_transcript, config)
        
        assert isinstance(result, dict)
        assert 'collection_info' in result
        assert 'video_metadata' in result
        assert 'transcript_analysis' in result
        assert 'content_summary' in result
        
        # Check collection info
        collection_info = result['collection_info']
        assert collection_info['collected_at'] == '2024-01-01T12:00:00'
        assert collection_info['collector_version'] == '1.0'
        assert collection_info['analysis_enabled'] is True
    
    @pytest.mark.unit
    def test_collect_comprehensive_metadata_none_video_info(self):
        """Test comprehensive metadata collection with None video_info."""
        result = collect_comprehensive_metadata(None, self.sample_transcript, {})
        
        assert isinstance(result, dict)
        assert result['collection_info']['analysis_enabled'] is False
        assert result['collection_info']['error'] == 'Video information unavailable'
        assert result['video_metadata'] == {}
        assert result['transcript_analysis'] == {}
        assert result['content_summary'] == {}
    
    @pytest.mark.unit
    def test_collect_comprehensive_metadata_no_transcript(self):
        """Test comprehensive metadata collection without transcript."""
        config = {"metadata_collection": {"enabled": True}}
        
        result = collect_comprehensive_metadata(self.sample_video_info, None, config)
        
        assert isinstance(result, dict)
        assert 'video_metadata' in result
        # Should still process video metadata even without transcript
        assert result['video_metadata']['basic_info']['video_id'] == 'test123'
    
    @pytest.mark.unit
    def test_collect_comprehensive_metadata_empty_transcript(self):
        """Test comprehensive metadata collection with empty transcript."""
        config = {"metadata_collection": {"enabled": True}}
        
        result = collect_comprehensive_metadata(self.sample_video_info, [], config)
        
        assert isinstance(result, dict)
        # Empty transcript should still allow video metadata processing
        assert result['video_metadata']['basic_info']['video_id'] == 'test123'


class TestMetadataCollectorEdgeCases:
    """Test edge cases and error conditions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.collector = MetadataCollector()
    
    @pytest.mark.unit
    def test_extract_keywords_empty_text(self):
        """Test keyword extraction with empty text."""
        keywords = self.collector._extract_keywords('', max_keywords=10)
        
        assert isinstance(keywords, list)
        assert len(keywords) == 0
    
    @pytest.mark.unit
    def test_extract_topics_no_topics(self):
        """Test topic extraction with text containing no topics."""
        text = 'the and or but in on at to for of with by'  # Only stop words
        
        topics = self.collector._extract_topics(text)
        
        assert isinstance(topics, list)
        # Should return empty or very few topics
    
    @pytest.mark.unit
    def test_analyze_language_non_english(self):
        """Test language analysis with non-English text."""
        spanish_text = 'Hola mundo, este es un texto en español con palabras específicas.'
        
        lang_analysis = self.collector._analyze_language(spanish_text)
        
        assert lang_analysis['detected_language'] == 'Unknown'
        assert lang_analysis['english_probability'] < 0.1
    
    @pytest.mark.unit
    def test_content_metrics_with_malformed_transcript(self):
        """Test content metrics with malformed transcript entries."""
        malformed_transcript = [
            {'text': 'Good entry', 'start': 0.0, 'duration': 2.0},
            {'start': 2.0, 'duration': 1.0},  # Missing text
            {'text': None, 'start': 3.0, 'duration': 1.0},  # None text
        ]
        
        full_text = 'Good entry'
        metrics = self.collector._calculate_content_metrics(full_text, malformed_transcript)
        
        # Should handle gracefully
        assert isinstance(metrics, dict)
        assert metrics['transcript_entries_count'] == len(malformed_transcript)
    
    @pytest.mark.unit
    def test_config_loading_error_handling(self):
        """Test graceful handling of config loading errors."""
        with patch('src.my_project.metadata_collector.load_config') as mock_load:
            mock_load.side_effect = Exception("Config error")
            
            # Should not crash, should use empty config
            collector = MetadataCollector()
            
            assert isinstance(collector.config, dict)
            # Should still be able to process metadata
            result = collector.extract_video_metadata({'id': 'test'})
            assert isinstance(result, dict)
