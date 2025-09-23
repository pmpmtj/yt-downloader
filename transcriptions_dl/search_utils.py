"""
Search utilities for transcript search functionality.
"""
from typing import List, Dict, Any, Optional, Tuple
from django.db.models import Q, QuerySet, Min, Max, Sum
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.core.paginator import Paginator
from django.conf import settings
from .models import Video, TranscriptSegment, Chapter, RawAsset


class TranscriptSearchEngine:
    """Advanced search engine for transcript content."""
    
    def __init__(self, user=None):
        """Initialize search engine for a specific user."""
        self.user = user
        self.base_queryset = Video.objects.filter(user=user) if user else Video.objects.all()
    
    def search_transcripts(
        self,
        query: str = "",
        search_type: str = "full_text",  # full_text, exact, fuzzy
        video_filters: Optional[Dict[str, Any]] = None,
        time_range: Optional[Tuple[float, float]] = None,
        language: Optional[str] = None,
        is_generated: Optional[bool] = None,
        sort_by: str = "relevance",  # relevance, date, duration, title
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """
        Perform comprehensive transcript search.
        
        Args:
            query: Search query text
            search_type: Type of search (full_text, exact, fuzzy)
            video_filters: Additional video filters (title, uploader, etc.)
            time_range: Time range filter (start_time, end_time) in seconds
            language: Language code filter
            is_generated: Filter by auto-generated content
            sort_by: Sort results by field
            page: Page number for pagination
            page_size: Number of results per page
            
        Returns:
            Dictionary with search results and metadata
        """
        # Start with base queryset
        videos_qs = self.base_queryset
        
        # Apply video-level filters
        if video_filters:
            videos_qs = self._apply_video_filters(videos_qs, video_filters)
        
        if language:
            videos_qs = videos_qs.filter(language_code=language)
        
        if is_generated is not None:
            videos_qs = videos_qs.filter(is_generated=is_generated)
        
        # If no query, return videos with basic info
        if not query.strip():
            return self._get_video_results(videos_qs, sort_by, page, page_size)
        
        # Search in transcript segments
        segments_qs = TranscriptSegment.objects.filter(video__in=videos_qs)
        
        # Apply time range filter to segments
        if time_range:
            start_time, end_time = time_range
            segments_qs = segments_qs.filter(
                start_time_s__gte=start_time,
                start_time_s__lte=end_time
            )
        
        # Apply search query
        if search_type == "full_text":
            segments_qs = self._full_text_search(segments_qs, query)
        elif search_type == "exact":
            segments_qs = segments_qs.filter(text__icontains=query)
        elif search_type == "fuzzy":
            segments_qs = self._fuzzy_search(segments_qs, query)
        
        # Get unique videos from matching segments
        video_ids = segments_qs.values_list('video_id', flat=True).distinct()
        matching_videos = videos_qs.filter(video_id__in=video_ids)
        
        # If no segments found, fallback to searching in raw assets
        if not video_ids and query.strip():
            matching_videos = self._search_in_raw_assets(videos_qs, query, search_type)
        
        # Apply sorting
        matching_videos = self._apply_sorting(matching_videos, sort_by, query)
        
        # Paginate results
        paginator = Paginator(matching_videos, page_size)
        page_obj = paginator.get_page(page)
        
        # Get detailed results with segments
        results = []
        for video in page_obj:
            video_segments = segments_qs.filter(video=video).order_by('start_time_s')
            
            # If no segments, create mock segments from raw assets for display
            if video_segments.count() == 0 and query.strip():
                mock_segments = self._create_mock_segments_from_raw_assets(video, query)
                total_segments = 1  # We found at least one match
            else:
                mock_segments = []
                total_segments = video_segments.count()
            
            results.append({
                'video': self._serialize_video(video),
                'matching_segments': self._serialize_segments(video_segments) + mock_segments,
                'total_segments': total_segments,
                'relevance_score': self._calculate_relevance_score(video, query)
            })
        
        return {
            'results': results,
            'total_count': paginator.count,
            'page': page,
            'page_size': page_size,
            'total_pages': paginator.num_pages,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
            'query': query,
            'search_type': search_type,
            'filters_applied': {
                'video_filters': video_filters or {},
                'time_range': time_range,
                'language': language,
                'is_generated': is_generated
            }
        }
    
    def search_chapters(
        self,
        query: str = "",
        video_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """Search within video chapters."""
        chapters_qs = Chapter.objects.filter(video__in=self.base_queryset)
        
        if video_id:
            chapters_qs = chapters_qs.filter(video__video_id=video_id)
        
        if query.strip():
            chapters_qs = chapters_qs.filter(
                Q(text__icontains=query) | Q(summary__icontains=query)
            )
        
        paginator = Paginator(chapters_qs, page_size)
        page_obj = paginator.get_page(page)
        
        results = []
        for chapter in page_obj:
            results.append({
                'id': chapter.id,
                'video_id': chapter.video.video_id,
                'video_title': chapter.video.title,
                'start_time_s': float(chapter.start_time_s),
                'end_time_s': float(chapter.end_time_s) if chapter.end_time_s else None,
                'text': chapter.text,
                'summary': chapter.summary,
                'duration_s': float(chapter.end_time_s - chapter.start_time_s) if chapter.end_time_s else None
            })
        
        return {
            'results': results,
            'total_count': paginator.count,
            'page': page,
            'page_size': page_size,
            'total_pages': paginator.num_pages,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
            'query': query
        }
    
    def get_video_transcript(
        self,
        video_id: str,
        format_type: str = "clean_text"
    ) -> Optional[Dict[str, Any]]:
        """Get full transcript for a specific video."""
        try:
            video = self.base_queryset.get(video_id=video_id)
            raw_asset = video.raw_assets.filter(kind=format_type).first()
            
            if not raw_asset:
                return None
            
            return {
                'video_id': video.video_id,
                'title': video.title,
                'format': format_type,
                'content': raw_asset.content_text or raw_asset.content_json,
                'is_json': raw_asset.content_json is not None,
                'stored_at': raw_asset.stored_at,
                'language_code': video.language_code,
                'is_generated': video.is_generated
            }
        except Video.DoesNotExist:
            return None
    
    def get_search_suggestions(
        self,
        partial_query: str,
        limit: int = 10
    ) -> List[str]:
        """Get search suggestions based on partial query."""
        if len(partial_query.strip()) < 2:
            return []
        
        # Search in video titles and segment text
        video_titles = self.base_queryset.filter(
            title__icontains=partial_query
        ).values_list('title', flat=True)[:limit//2]
        
        segment_texts = TranscriptSegment.objects.filter(
            video__in=self.base_queryset,
            text__icontains=partial_query
        ).values_list('text', flat=True)[:limit//2]
        
        # Extract potential keywords from segment texts
        suggestions = set()
        for text in segment_texts:
            words = text.lower().split()
            for word in words:
                if partial_query.lower() in word and len(word) > len(partial_query):
                    suggestions.add(word)
        
        # Combine and return suggestions
        all_suggestions = list(video_titles) + list(suggestions)
        return all_suggestions[:limit]
    
    def _apply_video_filters(self, queryset: QuerySet, filters: Dict[str, Any]) -> QuerySet:
        """Apply video-level filters."""
        if 'title' in filters:
            queryset = queryset.filter(title__icontains=filters['title'])
        
        if 'uploader' in filters:
            queryset = queryset.filter(uploader__icontains=filters['uploader'])
        
        if 'date_from' in filters:
            queryset = queryset.filter(processed_at__date__gte=filters['date_from'])
        
        if 'date_to' in filters:
            queryset = queryset.filter(processed_at__date__lte=filters['date_to'])
        
        if 'duration_min' in filters:
            queryset = queryset.filter(duration_s__gte=filters['duration_min'])
        
        if 'duration_max' in filters:
            queryset = queryset.filter(duration_s__lte=filters['duration_max'])
        
        return queryset
    
    def _full_text_search(self, queryset: QuerySet, query: str) -> QuerySet:
        """Perform full-text search using PostgreSQL search vectors."""
        search_query = SearchQuery(query, config='english')
        search_vector = SearchVector('text', config='english')
        
        return queryset.annotate(
            search=search_vector,
            rank=SearchRank(search_vector, search_query)
        ).filter(search=search_query).order_by('-rank')
    
    def _fuzzy_search(self, queryset: QuerySet, query: str) -> QuerySet:
        """Perform fuzzy search using similarity."""
        # This would require pg_trgm extension
        # For now, fall back to icontains
        return queryset.filter(text__icontains=query)
    
    def _apply_sorting(self, queryset: QuerySet, sort_by: str, query: str = "") -> QuerySet:
        """Apply sorting to queryset."""
        if sort_by == "relevance" and query:
            # For relevance, we'll sort by title match first, then by date
            # This is a simplified approach since we can't easily get rank on videos
            return queryset.order_by('-processed_at')
        elif sort_by == "date":
            return queryset.order_by('-processed_at')
        elif sort_by == "duration":
            return queryset.order_by('-duration_s')
        elif sort_by == "title":
            return queryset.order_by('title')
        else:
            return queryset.order_by('-processed_at')
    
    def _get_video_results(self, queryset: QuerySet, sort_by: str, page: int, page_size: int) -> Dict[str, Any]:
        """Get video results without segment search."""
        queryset = self._apply_sorting(queryset, sort_by)
        
        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page)
        
        results = []
        for video in page_obj:
            results.append({
                'video': self._serialize_video(video),
                'matching_segments': [],
                'total_segments': video.segments.count(),
                'relevance_score': 0.0
            })
        
        return {
            'results': results,
            'total_count': paginator.count,
            'page': page,
            'page_size': page_size,
            'total_pages': paginator.num_pages,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
            'query': "",
            'search_type': "none",
            'filters_applied': {}
        }
    
    def _serialize_video(self, video: Video) -> Dict[str, Any]:
        """Serialize video object for API response."""
        return {
            'video_id': video.video_id,
            'title': video.title,
            'duration_s': video.duration_s,
            'upload_date': video.upload_date,
            'uploader': video.uploader,
            'language_code': video.language_code,
            'is_generated': video.is_generated,
            'processed_at': video.processed_at,
            'text_word_count': video.text_word_count,
            'text_char_count': video.text_char_count,
            'chapters_count': video.chapters.count(),
            'segments_count': video.segments.count()
        }
    
    def _serialize_segments(self, segments: QuerySet) -> List[Dict[str, Any]]:
        """Serialize segment objects for API response."""
        return [
            {
                'id': seg.id,
                'start_time_s': float(seg.start_time_s),
                'duration_s': float(seg.duration_s),
                'text': seg.text,
                'is_generated': seg.is_generated,
                'source': seg.source
            }
            for seg in segments
        ]
    
    def _search_in_raw_assets(self, videos_qs: QuerySet, query: str, search_type: str) -> QuerySet:
        """Fallback search in raw assets when segments are not available."""
        from .models import RawAsset
        
        # Search in clean text and timestamped text assets
        raw_assets = RawAsset.objects.filter(
            video__in=videos_qs,
            kind__in=['clean_text', 'timestamped']
        )
        
        if search_type == "exact":
            raw_assets = raw_assets.filter(content_text__icontains=query)
        else:  # full_text or fuzzy
            raw_assets = raw_assets.filter(content_text__icontains=query)
        
        # Get unique videos from matching raw assets
        video_ids = raw_assets.values_list('video_id', flat=True).distinct()
        return videos_qs.filter(video_id__in=video_ids)
    
    def _create_mock_segments_from_raw_assets(self, video: Video, query: str) -> List[Dict[str, Any]]:
        """Create mock segments from raw assets for display purposes."""
        from .models import RawAsset
        
        # Get clean text asset
        clean_asset = video.raw_assets.filter(kind='clean_text').first()
        if not clean_asset or not clean_asset.content_text:
            return []
        
        content = clean_asset.content_text
        query_lower = query.lower()
        
        # Find the first occurrence of the query in the content
        content_lower = content.lower()
        start_pos = content_lower.find(query_lower)
        
        if start_pos == -1:
            return []
        
        # Create a mock segment around the found text
        # Get some context around the match
        context_start = max(0, start_pos - 100)
        context_end = min(len(content), start_pos + len(query) + 100)
        
        context_text = content[context_start:context_end]
        
        return [{
            'id': 0,  # Mock ID
            'start_time_s': 0.0,  # Mock time
            'duration_s': 3.0,  # Mock duration
            'text': context_text,
            'is_generated': video.is_generated,
            'source': 'raw_asset'
        }]
    
    def _calculate_relevance_score(self, video: Video, query: str) -> float:
        """Calculate relevance score for a video."""
        # Simple relevance calculation based on title match
        if not query:
            return 0.0
        
        query_lower = query.lower()
        title_lower = video.title.lower()
        
        if query_lower in title_lower:
            return 1.0
        else:
            return 0.5


def get_user_search_stats(user) -> Dict[str, Any]:
    """Get search statistics for a user."""
    videos = Video.objects.filter(user=user)
    
    return {
        'total_videos': videos.count(),
        'total_segments': TranscriptSegment.objects.filter(video__in=videos).count(),
        'total_chapters': Chapter.objects.filter(video__in=videos).count(),
        'languages': list(videos.values_list('language_code', flat=True).distinct()),
        'date_range': {
            'earliest': videos.aggregate(earliest=Min('processed_at'))['earliest'],
            'latest': videos.aggregate(latest=Max('processed_at'))['latest']
        },
        'total_duration_s': videos.aggregate(total=Sum('duration_s'))['total'] or 0
    }
