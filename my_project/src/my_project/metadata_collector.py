"""
metadata_collector.py

Rich metadata collection and content analysis for YouTube videos.
Provides contextual information, content metrics, and quality assessment for LLM analysis.
"""

import re
import json
from typing import Dict, List, Any, Optional, Tuple
from collections import Counter
from datetime import datetime
from pathlib import Path

# Import logging
from .logger_utils.logger_utils import setup_logger
from .utils.path_utils import load_config

# Setup logger for this module
logger = setup_logger("metadata_collector")


class MetadataCollector:
    """Collects and analyzes rich metadata from YouTube videos and transcripts."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize metadata collector with configuration."""
        if config is None:
            try:
                config = load_config()
            except Exception as e:
                logger.warning(f"Could not load config, using defaults: {e}")
                config = {}
        
        self.config = config.get("metadata_collection", {})
        self.content_analysis_config = self.config.get("content_analysis", {})
        self.video_metadata_config = self.config.get("video_metadata", {})
        self.quality_config = self.config.get("quality_assessment", {})
        
        # Load stop words from config with fallback
        self.stop_words = self._load_stop_words()
        
        logger.debug(f"MetadataCollector initialized with config: {self.config}")
    
    def _load_stop_words(self) -> set:
        """Load stop words from config with fallback to default list."""
        try:
            # Try to load from config
            config_stop_words = self.content_analysis_config.get("stop_words", [])
            if config_stop_words:
                stop_words_set = set(config_stop_words)
                logger.debug(f"Loaded {len(stop_words_set)} stop words from config")
                return stop_words_set
            else:
                # Fallback to default stop words
                logger.debug("No stop words in config, using fallback list")
                return self._get_default_stop_words()
        except Exception as e:
            logger.warning(f"Failed to load stop words from config: {e}")
            return self._get_default_stop_words()
    
    def _get_default_stop_words(self) -> set:
        """Get default stop words as fallback."""
        return {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
            'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
            'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must',
            'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they',
            'me', 'him', 'her', 'us', 'them', 'my', 'your', 'his', 'her', 'its', 'our', 'their'
        }

    def extract_video_metadata(self, video_info: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract comprehensive video metadata with defensive None handling."""
        logger.debug("Extracting video metadata")
        
        if video_info is None:
            logger.warning("video_info is None - returning empty metadata structure")
            return {
                'basic_info': {},
                'technical_details': {},
                'engagement_metrics': {},
                'channel_info': {},
                'content_details': {}
            }
        
        metadata = {
            'basic_info': self._extract_basic_info(video_info),
            'technical_details': {},
            'engagement_metrics': {},
            'channel_info': {},
            'content_details': {}
        }
        
        if self.video_metadata_config.get("technical_details", True):
            metadata['technical_details'] = self._extract_technical_details(video_info)
        
        if self.video_metadata_config.get("engagement_metrics", True):
            metadata['engagement_metrics'] = self._extract_engagement_metrics(video_info)
        
        if self.video_metadata_config.get("channel_info", True):
            metadata['channel_info'] = self._extract_channel_info(video_info)
        
        if self.video_metadata_config.get("detailed_description", True):
            metadata['content_details'] = self._extract_content_details(video_info)
        
        logger.info(f"Video metadata extracted: {len(metadata)} sections")
        return metadata
    
    def _extract_basic_info(self, video_info: Dict[str, Any]) -> Dict[str, Any]:
        """Extract basic video information."""
        return {
            'video_id': video_info.get('id', ''),
            'title': video_info.get('title', ''),
            'uploader': video_info.get('uploader', ''),
            'uploader_id': video_info.get('uploader_id', ''),
            'upload_date': video_info.get('upload_date', ''),
            'duration_seconds': video_info.get('duration', 0),
            'duration_readable': self._format_duration(video_info.get('duration', 0)),
            'webpage_url': video_info.get('webpage_url', ''),
            'original_url': video_info.get('original_url', ''),
            'extractor': video_info.get('extractor', ''),
            'extractor_key': video_info.get('extractor_key', '')
        }
    
    def _extract_technical_details(self, video_info: Dict[str, Any]) -> Dict[str, Any]:
        """Extract technical video details."""
        formats = video_info.get('formats', [])
        
        # Analyze available formats
        video_formats = [f for f in formats if f.get('vcodec') != 'none']
        audio_formats = [f for f in formats if f.get('acodec') != 'none' and f.get('vcodec') == 'none']
        
        max_resolution = 0
        available_qualities = set()
        codecs = set()
        
        for fmt in video_formats:
            height = fmt.get('height', 0)
            if height > max_resolution:
                max_resolution = height
            if height > 0:
                available_qualities.add(f"{height}p")
            
            vcodec = fmt.get('vcodec', '')
            if vcodec and vcodec != 'none':
                codecs.add(vcodec.split('.')[0])  # Get codec family
        
        return {
            'max_resolution': f"{max_resolution}p" if max_resolution > 0 else "Unknown",
            'available_qualities': sorted(list(available_qualities), key=lambda x: int(x[:-1]), reverse=True),
            'total_formats': len(formats),
            'video_formats_count': len(video_formats),
            'audio_formats_count': len(audio_formats),
            'video_codecs': list(codecs),
            'fps': video_info.get('fps'),
            'aspect_ratio': video_info.get('aspect_ratio'),
            'filesize_approx': video_info.get('filesize_approx'),
            'protocol': video_info.get('protocol'),
            'format_note': video_info.get('format_note')
        }
    
    def _extract_engagement_metrics(self, video_info: Dict[str, Any]) -> Dict[str, Any]:
        """Extract engagement and popularity metrics."""
        view_count = video_info.get('view_count', 0)
        like_count = video_info.get('like_count', 0)
        duration = video_info.get('duration', 1)
        
        # Calculate engagement rate (likes per view)
        engagement_rate = (like_count / view_count * 100) if view_count > 0 else 0
        
        # Calculate views per day (approximate)
        upload_date = video_info.get('upload_date', '')
        days_since_upload = self._calculate_days_since_upload(upload_date)
        views_per_day = (view_count / days_since_upload) if days_since_upload > 0 else 0
        
        return {
            'view_count': view_count,
            'like_count': like_count,
            'dislike_count': video_info.get('dislike_count'),
            'comment_count': video_info.get('comment_count'),
            'engagement_rate_percent': round(engagement_rate, 2),
            'views_per_day': round(views_per_day, 2),
            'days_since_upload': days_since_upload,
            'age_rating': video_info.get('age_limit'),
            'availability': video_info.get('availability'),
            'live_status': video_info.get('live_status'),
            'was_live': video_info.get('was_live', False)
        }
    
    def _extract_channel_info(self, video_info: Dict[str, Any]) -> Dict[str, Any]:
        """Extract channel information."""
        return {
            'channel': video_info.get('channel', ''),
            'channel_id': video_info.get('channel_id', ''),
            'channel_url': video_info.get('channel_url', ''),
            'channel_follower_count': video_info.get('channel_follower_count'),
            'uploader_url': video_info.get('uploader_url', ''),
            'playlist': video_info.get('playlist'),
            'playlist_id': video_info.get('playlist_id'),
            'playlist_index': video_info.get('playlist_index'),
            'playlist_title': video_info.get('playlist_title')
        }
    
    def _extract_content_details(self, video_info: Dict[str, Any]) -> Dict[str, Any]:
        """Extract detailed content information."""
        description = video_info.get('description', '')
        tags = video_info.get('tags', [])
        categories = video_info.get('categories', [])
        
        return {
            'description': description,
            'description_length': len(description),
            'tags': tags,
            'tag_count': len(tags),
            'categories': categories,
            'category_count': len(categories),
            'language': video_info.get('language'),
            'automatic_captions': list(video_info.get('automatic_captions', {}).keys()),
            'subtitles': list(video_info.get('subtitles', {}).keys()),
            'thumbnail': video_info.get('thumbnail'),
            'thumbnails_count': len(video_info.get('thumbnails', [])),
            'chapters': video_info.get('chapters', []),
            'chapter_count': len(video_info.get('chapters', []))
        }
    
    def analyze_transcript_content(self, transcript_entries: List[Dict], video_metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Perform content analysis on transcript."""
        logger.debug("Starting transcript content analysis")
        
        if not transcript_entries:
            return {}
        
        # Extract text content
        full_text = ' '.join([
            (entry.get('text', '') if isinstance(entry, dict) else getattr(entry, 'text', ''))
            for entry in transcript_entries
        ])
        
        analysis = {
            'content_metrics': self._calculate_content_metrics(full_text, transcript_entries),
            'quality_assessment': {},
            'content_analysis': {}
        }
        
        if self.quality_config.get("content_quality_score", True):
            analysis['quality_assessment'] = self._assess_content_quality(full_text, transcript_entries)
        
        if self.content_analysis_config.get("extract_keywords", True):
            analysis['content_analysis']['keywords'] = self._extract_keywords(full_text)
        
        if self.content_analysis_config.get("extract_topics", True):
            analysis['content_analysis']['topics'] = self._extract_topics(full_text)
        
        if self.content_analysis_config.get("detect_language", True):
            analysis['content_analysis']['language_analysis'] = self._analyze_language(full_text)
        
        if self.content_analysis_config.get("content_categorization", True):
            analysis['content_analysis']['content_type'] = self._categorize_content(full_text, video_metadata)
        
        logger.info(f"Transcript content analysis complete: {len(analysis)} categories")
        return analysis
    
    def _calculate_content_metrics(self, full_text: str, transcript_entries: List[Dict]) -> Dict[str, Any]:
        """Calculate content metrics."""
        words = full_text.split()
        sentences = re.split(r'[.!?]+', full_text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        # Calculate speaking rate
        total_duration = 0
        if transcript_entries:
            try:
                last_entry = transcript_entries[-1]
                total_duration = float(last_entry.get('start', 0) if isinstance(last_entry, dict) 
                                     else getattr(last_entry, 'start', 0))
            except (ValueError, AttributeError):
                total_duration = 0
        
        speaking_rate = (len(words) / (total_duration / 60)) if total_duration > 0 else 0
        
        return {
            'word_count': len(words),
            'sentence_count': len(sentences),
            'character_count': len(full_text),
            'character_count_no_spaces': len(full_text.replace(' ', '')),
            'average_words_per_sentence': len(words) / len(sentences) if sentences else 0,
            'average_sentence_length': sum(len(s) for s in sentences) / len(sentences) if sentences else 0,
            'speaking_rate_wpm': round(speaking_rate, 1),
            'estimated_reading_time_minutes': round(len(words) / 200, 1),
            'lexical_diversity': len(set(words)) / len(words) if words else 0,
            'total_duration_seconds': total_duration,
            'transcript_entries_count': len(transcript_entries)
        }
    
    def _assess_content_quality(self, full_text: str, transcript_entries: List[Dict]) -> Dict[str, Any]:
        """Assess content quality indicators."""
        # Count common transcription artifacts
        artifacts = [
            '[Music]', '[Applause]', '[Laughter]', '[Noise]', '[Inaudible]',
            'um', 'uh', 'er', 'ah', '...', '--'
        ]
        
        artifact_count = sum(full_text.lower().count(artifact.lower()) for artifact in artifacts)
        
        # Assess transcript completeness
        incomplete_indicators = ['[', ']', '...', '--', 'inaudible', 'unclear']
        incomplete_count = sum(full_text.lower().count(indicator) for indicator in incomplete_indicators)
        
        # Calculate quality score (0-100)
        words = full_text.split()
        artifact_ratio = artifact_count / len(words) if words else 0
        incomplete_ratio = incomplete_count / len(words) if words else 0
        
        quality_score = max(0, 100 - (artifact_ratio * 100) - (incomplete_ratio * 50))
        
        # Assess entry consistency
        entry_lengths = []
        for entry in transcript_entries:
            try:
                text = entry.get('text', '') if isinstance(entry, dict) else getattr(entry, 'text', '')
                entry_lengths.append(len(text))
            except AttributeError:
                continue
        
        avg_entry_length = sum(entry_lengths) / len(entry_lengths) if entry_lengths else 0
        entry_consistency = 1 - (max(entry_lengths) - min(entry_lengths)) / max(entry_lengths) if entry_lengths else 0
        
        return {
            'quality_score': round(quality_score, 1),
            'artifact_count': artifact_count,
            'artifact_ratio': round(artifact_ratio, 3),
            'incomplete_indicators': incomplete_count,
            'incomplete_ratio': round(incomplete_ratio, 3),
            'average_entry_length': round(avg_entry_length, 1),
            'entry_consistency': round(entry_consistency, 2),
            'quality_category': self._categorize_quality(quality_score)
        }
    
    def _extract_keywords(self, text: str, max_keywords: int = 20) -> List[Dict[str, Any]]:
        """Extract keywords from text."""
        # Clean and tokenize
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        
        # Remove stop words
        meaningful_words = [word for word in words if word not in self.stop_words]
        
        # Count frequency
        word_freq = Counter(meaningful_words)
        
        # Get top keywords
        top_keywords = word_freq.most_common(max_keywords)
        
        return [
            {
                'keyword': word,
                'frequency': freq,
                'relevance_score': round(freq / len(meaningful_words) * 100, 2)
            }
            for word, freq in top_keywords
        ]
    
    def _extract_topics(self, text: str) -> List[str]:
        """Extract potential topics from text using simple heuristics."""
        # Look for topic indicators
        topic_patterns = [
            r'\b(?:about|regarding|concerning|discussing|topic|subject)\s+([a-zA-Z\s]{3,20})',
            r'\b(?:today we\'ll|we\'re going to|let\'s talk about|focus on)\s+([a-zA-Z\s]{3,20})',
            r'\b(?:introduction to|overview of|guide to|tutorial on)\s+([a-zA-Z\s]{3,20})'
        ]
        
        topics = []
        for pattern in topic_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            topics.extend([match.strip().title() for match in matches])
        
        # Also extract capitalized phrases (potential proper nouns/topics)
        capitalized_phrases = re.findall(r'\b[A-Z][a-zA-Z]*(?:\s+[A-Z][a-zA-Z]*){0,2}\b', text)
        
        # Filter and deduplicate
        all_topics = list(set(topics + capitalized_phrases))
        
        # Remove single words and very short phrases
        filtered_topics = [topic for topic in all_topics if len(topic.split()) > 1 and len(topic) > 5]
        
        return filtered_topics[:10]  # Return top 10
    
    def _analyze_language(self, text: str) -> Dict[str, Any]:
        """Basic language analysis."""
        # Simple language detection heuristics
        common_english_words = ['the', 'and', 'to', 'of', 'a', 'in', 'is', 'it', 'you', 'that']
        english_word_count = sum(1 for word in text.lower().split() if word in common_english_words)
        total_words = len(text.split())
        
        english_probability = english_word_count / total_words if total_words > 0 else 0
        
        # Readability indicators
        sentences = re.split(r'[.!?]+', text)
        words = text.split()
        avg_words_per_sentence = len(words) / len(sentences) if sentences else 0
        
        # Simple complexity score
        complex_words = len([word for word in words if len(word) > 6])
        complexity_ratio = complex_words / len(words) if words else 0
        
        return {
            'detected_language': 'English' if english_probability > 0.1 else 'Unknown',
            'english_probability': round(english_probability, 2),
            'average_words_per_sentence': round(avg_words_per_sentence, 1),
            'complexity_ratio': round(complexity_ratio, 2),
            'readability_level': self._assess_readability(avg_words_per_sentence, complexity_ratio)
        }
    
    def _categorize_content(self, text: str, video_metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Categorize content type."""
        text_lower = text.lower()
        
        # Educational indicators
        educational_keywords = ['learn', 'tutorial', 'explain', 'how to', 'guide', 'lesson', 'course', 'teach']
        educational_score = sum(1 for keyword in educational_keywords if keyword in text_lower)
        
        # Entertainment indicators
        entertainment_keywords = ['funny', 'entertainment', 'comedy', 'music', 'game', 'play', 'fun']
        entertainment_score = sum(1 for keyword in entertainment_keywords if keyword in text_lower)
        
        # News/Documentary indicators
        news_keywords = ['news', 'report', 'documentary', 'interview', 'analysis', 'breaking']
        news_score = sum(1 for keyword in news_keywords if keyword in text_lower)
        
        # Technical indicators
        technical_keywords = ['technology', 'software', 'programming', 'computer', 'technical', 'development']
        technical_score = sum(1 for keyword in technical_keywords if keyword in text_lower)
        
        # Determine primary category
        scores = {
            'Educational': educational_score,
            'Entertainment': entertainment_score,
            'News/Documentary': news_score,
            'Technical': technical_score
        }
        
        primary_category = max(scores, key=scores.get) if any(scores.values()) else 'General'
        
        return {
            'primary_category': primary_category,
            'category_scores': scores,
            'confidence': round(max(scores.values()) / sum(scores.values()) * 100, 1) if sum(scores.values()) > 0 else 0
        }
    
    def _format_duration(self, seconds: int) -> str:
        """Format duration in human-readable format."""
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            minutes = seconds // 60
            secs = seconds % 60
            return f"{minutes}m {secs}s"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            secs = seconds % 60
            return f"{hours}h {minutes}m {secs}s"
    
    def _calculate_days_since_upload(self, upload_date: str) -> int:
        """Calculate days since upload."""
        if not upload_date or len(upload_date) != 8:
            return 0
        
        try:
            upload_datetime = datetime.strptime(upload_date, '%Y%m%d')
            days_diff = (datetime.now() - upload_datetime).days
            return max(1, days_diff)  # At least 1 day
        except ValueError:
            return 0
    
    def _categorize_quality(self, quality_score: float) -> str:
        """Categorize quality score."""
        if quality_score >= 90:
            return "Excellent"
        elif quality_score >= 80:
            return "Very Good"
        elif quality_score >= 70:
            return "Good"
        elif quality_score >= 60:
            return "Fair"
        elif quality_score >= 50:
            return "Poor"
        else:
            return "Very Poor"
    
    def _assess_readability(self, avg_words_per_sentence: float, complexity_ratio: float) -> str:
        """Assess readability level."""
        if avg_words_per_sentence < 15 and complexity_ratio < 0.2:
            return "Easy"
        elif avg_words_per_sentence < 20 and complexity_ratio < 0.3:
            return "Moderate"
        elif avg_words_per_sentence < 25 and complexity_ratio < 0.4:
            return "Difficult"
        else:
            return "Very Difficult"
    
    def generate_content_summary(self, video_info: Optional[Dict[str, Any]], transcript_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive content summary with defensive None handling."""
        logger.debug("Generating content summary")
        
        if video_info is None:
            logger.warning("video_info is None - returning minimal content summary")
            return {
                'overview': {
                    'title': 'Unknown',
                    'duration': 'Unknown',
                    'uploader': 'Unknown', 
                    'upload_date': 'Unknown',
                    'view_count': 0
                },
                'content_insights': {},
                'quality_indicators': {},
                'llm_suitability': {'overall_score': 0, 'recommended_for_llm': False}
            }
        
        # Extract key information
        video_metadata = self.extract_video_metadata(video_info)
        
        # Create summary
        summary = {
            'overview': {
                'title': video_info.get('title', ''),
                'duration': video_metadata['basic_info'].get('duration_readable', 'Unknown'),
                'uploader': video_info.get('uploader', ''),
                'upload_date': video_info.get('upload_date', ''),
                'view_count': video_metadata.get('engagement_metrics', {}).get('view_count', 0)
            },
            'content_insights': {},
            'quality_indicators': {},
            'llm_suitability': {}
        }
        
        # Add content insights
        if transcript_analysis.get('content_analysis'):
            content_analysis = transcript_analysis['content_analysis']
            summary['content_insights'] = {
                'primary_topics': content_analysis.get('topics', [])[:5],
                'key_keywords': [kw['keyword'] for kw in content_analysis.get('keywords', [])[:10]],
                'content_category': content_analysis.get('content_type', {}).get('primary_category', 'Unknown'),
                'language': content_analysis.get('language_analysis', {}).get('detected_language', 'Unknown')
            }
        
        # Add quality indicators
        if transcript_analysis.get('quality_assessment'):
            quality = transcript_analysis['quality_assessment']
            summary['quality_indicators'] = {
                'overall_quality': quality.get('quality_category', 'Unknown'),
                'quality_score': quality.get('quality_score', 0),
                'transcript_completeness': 100 - (quality.get('incomplete_ratio', 0) * 100)
            }
        
        # Add LLM suitability assessment
        content_metrics = transcript_analysis.get('content_metrics', {})
        summary['llm_suitability'] = self._assess_llm_suitability(content_metrics, transcript_analysis.get('quality_assessment', {}))
        
        logger.info("Content summary generated successfully")
        return summary
    
    def _assess_llm_suitability(self, content_metrics: Dict, quality_assessment: Dict) -> Dict[str, Any]:
        """Assess how suitable content is for LLM analysis."""
        word_count = content_metrics.get('word_count', 0)
        quality_score = quality_assessment.get('quality_score', 0)
        
        # Length suitability
        if word_count < 50:
            length_suitability = "Too Short"
        elif word_count < 200:
            length_suitability = "Short but Usable"
        elif word_count < 2000:
            length_suitability = "Ideal Length"
        elif word_count < 5000:
            length_suitability = "Long but Manageable"
        else:
            length_suitability = "Very Long - Consider Chunking"
        
        # Overall suitability score
        length_score = min(100, (word_count / 1000) * 50) if word_count <= 2000 else max(50, 100 - (word_count - 2000) / 100)
        overall_score = (length_score * 0.3) + (quality_score * 0.7)
        
        return {
            'overall_score': round(overall_score, 1),
            'length_suitability': length_suitability,
            'recommended_for_llm': overall_score >= 70,
            'processing_notes': self._generate_processing_notes(content_metrics, quality_assessment)
        }
    
    def _generate_processing_notes(self, content_metrics: Dict, quality_assessment: Dict) -> List[str]:
        """Generate processing recommendations."""
        notes = []
        
        word_count = content_metrics.get('word_count', 0)
        quality_score = quality_assessment.get('quality_score', 0)
        artifact_ratio = quality_assessment.get('artifact_ratio', 0)
        
        if word_count > 3000:
            notes.append("Consider breaking into smaller chunks for better LLM processing")
        
        if quality_score < 70:
            notes.append("Low quality transcript - may need manual review")
        
        if artifact_ratio > 0.1:
            notes.append("High artifact content - clean format recommended")
        
        if content_metrics.get('speaking_rate_wpm', 0) > 200:
            notes.append("Fast-paced content - may have accuracy issues")
        
        if not notes:
            notes.append("Good quality content suitable for direct LLM analysis")
        
        return notes


def collect_comprehensive_metadata(video_info: Optional[Dict[str, Any]], transcript_entries: List[Dict] = None, 
                                 config: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Collect comprehensive metadata for video and transcript.
    
    Args:
        video_info: Video information from yt-dlp (can be None on extraction failure)
        transcript_entries: Transcript entries if available
        config: Configuration dictionary
    
    Returns:
        Dictionary with comprehensive metadata
    """
    logger.info("Starting comprehensive metadata collection")
    
    if video_info is None:
        logger.warning("video_info is None - returning minimal metadata structure")
        return {
            'collection_info': {
                'collected_at': datetime.now().isoformat(),
                'collector_version': '1.0',
                'analysis_enabled': False,
                'error': 'Video information unavailable'
            },
            'video_metadata': {},
            'transcript_analysis': {},
            'content_summary': {}
        }
    
    collector = MetadataCollector(config)
    
    # Collect video metadata
    video_metadata = collector.extract_video_metadata(video_info)
    
    # Analyze transcript if available
    transcript_analysis = {}
    if transcript_entries:
        transcript_analysis = collector.analyze_transcript_content(transcript_entries, video_metadata)
    
    # Generate content summary
    content_summary = collector.generate_content_summary(video_info, transcript_analysis)
    
    # Combine all metadata
    comprehensive_metadata = {
        'collection_info': {
            'collected_at': datetime.now().isoformat(),
            'collector_version': '1.0',
            'analysis_enabled': collector.config.get('enabled', True)
        },
        'video_metadata': video_metadata,
        'transcript_analysis': transcript_analysis,
        'content_summary': content_summary
    }
    
    logger.info("Comprehensive metadata collection complete")
    return comprehensive_metadata
