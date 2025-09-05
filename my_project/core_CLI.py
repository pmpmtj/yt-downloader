# core_cli.py
"""
core_CLI.py

Command-line interface (CLI) for downloading YouTube content.
Accepts user arguments for URL, language, download type, quality, etc.

Run example:
    python core_CLI.py https://youtube.com/xyz --audio --transcript
"""

import argparse
import os

# Import from utils within the package
from .utils.path_utils import (
    get_downloads_directory, 
    generate_session_uuid, 
    generate_video_uuid,
    create_download_structure
)
from .core import (
    get_video_info,
    select_default_audio,
    select_default_video,
    select_combined_video_audio,
    select_combined_with_lang,
    select_video_plus_audio_with_lang,
    build_format_string,
    print_basic_info,
    print_audio_formats,
    print_video_formats,
    print_available_audio_languages,
    print_and_select_default_transcript,
    print_transcript_preview,
    list_transcript_metadata,
    _lang_matches,
    _fmt_audio_lang
)
from .yt_downloads_utils import (
    download_audio,
    download_video,
    download_video_with_audio,
    download_transcript,
    get_filename_template
)

# Import logging
from .logger_utils.logger_utils import setup_logger

# Setup logger for this module
logger = setup_logger("core_CLI")


def download_audio_with_fallback(url: str, audio_formats: list, save_path: str, max_format_attempts: int = 3) -> bool:
    """Download audio with format fallback on failure."""
    from .core import smart_audio_selection
    
    try:
        from .utils.path_utils import load_normalized_config
        config = load_normalized_config()
        audio_prefs = config.get("quality_preferences", {}).get("audio", {})
        network_config = config.get("network", {})
        max_retries = network_config.get("max_retries", 3)
        retry_delay = network_config.get("retry_delay_seconds", 2)
    except:
        audio_prefs = {}
        max_retries, retry_delay = 3, 2
    
    # Try multiple format options
    for attempt in range(min(max_format_attempts, len(audio_formats))):
        try:
            # Get best format for this attempt
            remaining_formats = audio_formats[attempt:]
            selected_format = smart_audio_selection(remaining_formats, audio_prefs)
            
            if not selected_format:
                print(f"ðŸ”„ No more audio formats to try (attempt {attempt + 1})")
                continue
                
            format_id = selected_format.get("format_id")
            print(f"ðŸ”„ Audio format attempt {attempt + 1}: {format_id} - {selected_format.get('format_note')}")
            
            # Try download with this format
            success = download_audio(url, format_id, save_path, max_retries, retry_delay)
            if success:
                return True
                
        except Exception as e:
            print(f"âŒ Audio format {attempt + 1} failed: {str(e)}")
            continue
    
    return False


def download_video_with_fallback(url: str, video_formats: list, save_path: str, max_format_attempts: int = 3) -> bool:
    """Download video with format fallback on failure."""
    from .core import smart_video_selection
    
    try:
        from .utils.path_utils import load_normalized_config
        config = load_normalized_config()
        video_prefs = config.get("quality_preferences", {}).get("video", {})
        network_config = config.get("network", {})
        max_retries = network_config.get("max_retries", 3)
        retry_delay = network_config.get("retry_delay_seconds", 2)
    except:
        video_prefs = {}
        max_retries, retry_delay = 3, 2
    
    # Try multiple format options
    for attempt in range(min(max_format_attempts, len(video_formats))):
        try:
            # Get best format for this attempt
            remaining_formats = video_formats[attempt:]
            selected_format = smart_video_selection(remaining_formats, video_prefs)
            
            if not selected_format:
                print(f"ðŸ”„ No more video formats to try (attempt {attempt + 1})")
                continue
                
            format_id = selected_format.get("format_id")
            print(f"ðŸ”„ Video format attempt {attempt + 1}: {format_id} - {selected_format.get('format_note')} - {selected_format.get('height')}p")
            
            # Try download with this format
            success = download_video(url, format_id, save_path, max_retries, retry_delay)
            if success:
                return True
                
        except Exception as e:
            print(f"âŒ Video format {attempt + 1} failed: {str(e)}")
            continue
    
    return False

def parse_args(args=None):
    parser = argparse.ArgumentParser(
        description="YouTube Downloader CLI â€” select language, quality, media types"
    )

    parser.add_argument("urls", nargs="*", help="YouTube video URL(s) or playlist URL(s) to process")
    parser.add_argument("--lang", type=str, default=None, help="Preferred transcript/audio language (e.g. en, pt-BR)")
    parser.add_argument("--quality", type=str, default=None, help="Preferred video quality (e.g. 720p, 1080p)")
    parser.add_argument("--audio", action="store_true", help="Download audio only")
    parser.add_argument("--video-only", action="store_true", help="Download video only (silent - no audio)")
    parser.add_argument("--video-with-audio", action="store_true", help="Download video with audio included")
    parser.add_argument("--transcript", action="store_true", help="Download transcript only (if available)")
    parser.add_argument("--transcript-formats", type=str, nargs="+", 
                        choices=["clean", "timestamped", "structured", "all"],
                        help="Transcript formats to generate (clean, timestamped, structured, all). Default: timestamped")
    parser.add_argument("--preview-transcript", action="store_true", 
                        help="Show transcript preview before downloading")
    parser.add_argument("--metadata-analysis", action="store_true",
                        help="Enable comprehensive metadata analysis (keywords, topics, quality assessment)")
    parser.add_argument("--metadata-export", type=str, choices=["json", "csv", "markdown"],
                        help="Export metadata to specified format (json, csv, markdown)")
    parser.add_argument("--info-only", action="store_true", help="Only fetch and display info (no download)")
    parser.add_argument("--outdir", type=str, default=".", help="Directory to save downloaded files")
    parser.add_argument("--batch-file", type=str, help="File containing URLs (one per line)")
    parser.add_argument("--max-videos", type=int, default=None, help="Maximum number of videos to process from playlists")
    parser.add_argument("--playlist-start", type=int, default=1, help="Playlist video to start at (default: 1)")
    parser.add_argument("--playlist-end", type=int, default=None, help="Playlist video to end at")
    parser.add_argument("--audio-lang", nargs="+", help="Preferred audio language(s), e.g., en pt-PT pt-BR. If unavailable, falls back unless --require-audio-lang is set.")
    parser.add_argument("--require-audio-lang", action="store_true", help="Fail if the requested audio language is not available.")
    parser.add_argument("--print-config", action="store_true", help="Print effective configuration and exit")

    return parser.parse_args(args)


def process_single_video(url: str, session_uuid: str, base_downloads_dir: str, args) -> dict:
    """Process a single video URL and return results with database logging."""
    try:
        print(f"\n{'='*60}")
        print(f"Processing: {url}")
        print(f"{'='*60}")
        
        # ðŸ†• Use database-aware download manager for logging
        from .download_manager import get_download_manager
        download_manager = get_download_manager()
        
        # Convert args to dict if needed
        if hasattr(args, '__dict__'):
            args_dict = {
                'audio': getattr(args, 'audio', False),
                'video_only': getattr(args, 'video_only', False),
                'video_with_audio': getattr(args, 'video_with_audio', False),
                'transcript': getattr(args, 'transcript', False),
                'quality': getattr(args, 'quality', None),
                'lang': getattr(args, 'lang', None),
                'audio_lang': getattr(args, 'audio_lang', []),
                'require_audio_lang': getattr(args, 'require_audio_lang', False),
                'transcript_formats': getattr(args, 'transcript_formats', None),
                'preview_transcript': getattr(args, 'preview_transcript', False),
                'metadata_export': getattr(args, 'metadata_export', None),
                'info_only': getattr(args, 'info_only', False)
            }
        else:
            args_dict = args
        
        # Check for info-only mode before database operations
        if args_dict.get('info_only') or not (args_dict.get('audio') or args_dict.get('video_only') or args_dict.get('video_with_audio') or args_dict.get('transcript')):
            # Handle info-only mode without database logging (existing behavior)
            return process_info_only_mode(url, session_uuid, base_downloads_dir, args)
        
        # Use database-aware download for actual downloads
        logger.info(f"ðŸ”„ Starting database-aware download for {url}")
        return download_manager.run_download_with_db(url, session_uuid, base_downloads_dir, args_dict)
        
    except Exception as e:
        print(f"ðŸ’¥ Error processing video {url}: {str(e)}")
        logger.error(f"Error processing video {url}: {str(e)}")
        return {"status": "error", "url": url, "error": str(e)}


def process_info_only_mode(url: str, session_uuid: str, base_downloads_dir: str, args) -> dict:
    """Handle info-only mode (original logic without database logging)."""
    try:
        # Step 1: Fetch video info
        info = get_video_info(url)
        if info is None:
            print("âŒ Failed to extract video information. Video may be private, deleted, or URL is invalid.")
            return {"status": "error", "error": "Failed to extract video info", "video_id": None, "title": None}
        
        print_basic_info(info)
        formats = info.get("formats", [])

        # Step 2: Generate video UUID for this specific video
        video_uuid = generate_video_uuid()
        print(f"Video UUID: {video_uuid}")

        # Step 3: Select defaults with quality override from CLI
        # Handle args properly whether it's an object or dict
        quality = getattr(args, 'quality', None) if hasattr(args, 'quality') else args.get('quality')
        lang = getattr(args, 'lang', None) if hasattr(args, 'lang') else args.get('lang')
        audio_lang = getattr(args, 'audio_lang', []) if hasattr(args, 'audio_lang') else args.get('audio_lang', [])
        require_audio_lang = getattr(args, 'require_audio_lang', False) if hasattr(args, 'require_audio_lang') else args.get('require_audio_lang', False)
        preview_transcript = getattr(args, 'preview_transcript', False) if hasattr(args, 'preview_transcript') else args.get('preview_transcript', False)
        video_with_audio = getattr(args, 'video_with_audio', False) if hasattr(args, 'video_with_audio') else args.get('video_with_audio', False)
        
        default_audio, audio_list = select_default_audio(formats, quality_override=quality)
        default_video, video_list = select_default_video(formats, quality_override=quality)
        default_combined, combined_list = select_combined_video_audio(formats, quality_override=quality) if video_with_audio else (None, [])
        default_transcript = print_and_select_default_transcript(info.get("id"), preferred_language=lang)
        
        # Show transcript preview if requested
        if preview_transcript and default_transcript:
            print_transcript_preview(info.get("id"), default_transcript.get("language_code"))

        # Step 4: Print info
        print_audio_formats(audio_list, default_audio)
        print_video_formats(video_list, default_video)
        if combined_list:
            print_video_formats(combined_list, default_combined)  # Combined formats display as video formats
        
        # Show available audio languages
        print_available_audio_languages(formats)
        
        print("\n=== Defaults Selected ===")
        if default_audio:
            print(f"Default audio: [{default_audio.get('format_id')}] {default_audio.get('ext')} | {default_audio.get('format_note')}")
        if default_video:
            print(f"Default video: [{default_video.get('format_id')}] {default_video.get('ext')} | {default_video.get('format_note')}")
        if default_combined:
            print(f"Default video+audio: [{default_combined.get('format_id')}] {default_combined.get('ext')} | {default_combined.get('format_note')} | {default_combined.get('height')}p")
        if default_transcript:
            print(f"Default transcript language: {default_transcript.get('language')}")
        
        # Show audio language preferences if specified
        if audio_lang:
            print(f"Preferred audio languages: {', '.join(audio_lang)}")
            if require_audio_lang:
                print("Strict language requirement: ENABLED")
        
        print(f"\nWould download to structure: {base_downloads_dir}/{session_uuid}/{video_uuid}/[audio|video|video_with_audio|transcripts]/")
        return {"status": "info_only", "video_id": info.get("id"), "title": info.get("title")}

    except Exception as e:
        print(f"ðŸ’¥ Error processing video {url}: {str(e)}")
        return {"status": "error", "url": url, "error": str(e)}


def print_effective_config(args):
    """Print the effective configuration after CLI overrides."""
    try:
        from .utils.path_utils import load_normalized_config
        config = load_normalized_config()
        
        print("=" * 60)
        print("EFFECTIVE CONFIGURATION")
        print("=" * 60)
        
        # Apply CLI overrides to show effective values
        effective_config = config.copy()
        
        # Show quality overrides
        if hasattr(args, 'quality') and args.quality:
            print(f"\nðŸ”§ CLI Override: --quality {args.quality}")
            if "quality_preferences" not in effective_config:
                effective_config["quality_preferences"] = {}
            if "video" not in effective_config["quality_preferences"]:
                effective_config["quality_preferences"]["video"] = {}
            if "audio" not in effective_config["quality_preferences"]:
                effective_config["quality_preferences"]["audio"] = {}
            
            effective_config["quality_preferences"]["video"]["preferred_quality"] = args.quality
            effective_config["quality_preferences"]["audio"]["preferred_quality"] = args.quality
        
        # Show transcript formats overrides
        if hasattr(args, 'transcript_formats') and args.transcript_formats:
            print(f"\nðŸ”§ CLI Override: --transcript-formats {args.transcript_formats}")
            if "transcripts" not in effective_config:
                effective_config["transcripts"] = {}
            if "processing" not in effective_config["transcripts"]:
                effective_config["transcripts"]["processing"] = {}
            effective_config["transcripts"]["processing"]["output_formats_list"] = args.transcript_formats
        
        # Show audio language overrides
        if hasattr(args, 'audio_lang') and args.audio_lang:
            print(f"\nðŸ”§ CLI Override: --audio-lang {args.audio_lang}")
            if "quality_preferences" not in effective_config:
                effective_config["quality_preferences"] = {}
            if "audio" not in effective_config["quality_preferences"]:
                effective_config["quality_preferences"]["audio"] = {}
            effective_config["quality_preferences"]["audio"]["preferred_languages"] = args.audio_lang
        
        if hasattr(args, 'require_audio_lang') and args.require_audio_lang:
            print(f"\nðŸ”§ CLI Override: --require-audio-lang")
            if "quality_preferences" not in effective_config:
                effective_config["quality_preferences"] = {}
            if "audio" not in effective_config["quality_preferences"]:
                effective_config["quality_preferences"]["audio"] = {}
            effective_config["quality_preferences"]["audio"]["require_language_match"] = True
        
        # Show output directory override
        if hasattr(args, 'outdir') and args.outdir and args.outdir != ".":
            print(f"\nðŸ”§ CLI Override: --outdir {args.outdir}")
            effective_config["downloads"]["base_directory"] = args.outdir
        
        # Pretty print the effective configuration
        import json
        print("\nðŸ“‹ Configuration JSON:")
        print(json.dumps(effective_config, indent=2, ensure_ascii=False))
        
        # Show key selections that will be used
        print("\n" + "=" * 60)
        print("KEY EFFECTIVE SETTINGS")
        print("=" * 60)
        
        video_prefs = effective_config.get("quality_preferences", {}).get("video", {})
        audio_prefs = effective_config.get("quality_preferences", {}).get("audio", {})
        transcript_prefs = effective_config.get("transcripts", {}).get("processing", {})
        
        print(f"ðŸ“¹ Video Quality: {video_prefs.get('preferred_quality', 'DEFAULT')}")
        print(f"ðŸŽµ Audio Quality: {audio_prefs.get('preferred_quality', 'DEFAULT')}")
        print(f"ðŸŽµ Audio Languages: {audio_prefs.get('preferred_languages', ['DEFAULT'])}")
        print(f"ðŸ”’ Require Audio Language: {audio_prefs.get('require_language_match', 'DEFAULT')}")
        print(f"ðŸ“ Transcript Formats: {transcript_prefs.get('output_formats_list', ['DEFAULT'])}")
        print(f"ðŸ“ Output Directory: {effective_config.get('downloads', {}).get('base_directory', 'DEFAULT')}")
        print(f"ðŸ”§ Sanitize Filenames: {effective_config.get('behavior', {}).get('sanitize_filenames', 'DEFAULT')}")
        print(f"ðŸ“ Max Filename Length: {effective_config.get('behavior', {}).get('max_filename_length', 'DEFAULT')}")
        
        print("=" * 60)
        
    except Exception as e:
        print(f"âŒ Error loading configuration: {e}")


def main():
    args = parse_args()
    
    # Handle --print-config flag
    if args.print_config:
        print_effective_config(args)
        return
    
    # Step 1: Collect all URLs to process
    urls_to_process = []
    
    # Add URLs from command line arguments
    urls_to_process.extend(args.urls)
    
    # Add URLs from batch file if provided
    if args.batch_file:
        try:
            with open(args.batch_file, 'r', encoding='utf-8') as f:
                batch_urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                urls_to_process.extend(batch_urls)
                print(f"ðŸ“ Loaded {len(batch_urls)} URLs from batch file: {args.batch_file}")
        except Exception as e:
            print(f"âŒ Error reading batch file {args.batch_file}: {str(e)}")
            return
    
    if not urls_to_process:
        print("âŒ No URLs provided to process")
        return
    
    # Step 2: Expand playlists and validate URLs
    expanded_urls = []
    for url in urls_to_process:
        try:
            expanded = expand_url(url, args.max_videos, args.playlist_start, args.playlist_end)
            expanded_urls.extend(expanded)
        except Exception as e:
            print(f"âš ï¸ Error expanding URL {url}: {str(e)}")
            expanded_urls.append(url)  # Add as-is if expansion fails
    
    print(f"\nðŸŽ¯ Total videos to process: {len(expanded_urls)}")
    
    # Step 3: Generate session UUID and determine output directory
    session_uuid = generate_session_uuid()
    print(f"Session UUID: {session_uuid}")
    
    if args.outdir and args.outdir != ".":
        base_downloads_dir = args.outdir
    else:
        base_downloads_dir = str(get_downloads_directory())
    
    print(f"Base downloads directory: {base_downloads_dir}")

    # Step 4: Process each video
    all_results = []
    total_success = 0
    total_processed = 0
    
    for i, url in enumerate(expanded_urls, 1):
        print(f"\nðŸŽ¬ Processing video {i}/{len(expanded_urls)}")
        result = process_single_video(url, session_uuid, base_downloads_dir, args)
        all_results.append(result)
        
        if result.get("status") == "processed":
            total_success += result.get("success_count", 0)
            total_processed += result.get("total_requested", 0)
    
    # Step 5: Final summary
    print(f"\n{'='*80}")
    print(f"ðŸŽ¯ BATCH PROCESSING COMPLETE")
    print(f"{'='*80}")
    print(f"ðŸ“Š Overall Summary:")
    print(f"   â€¢ Videos processed: {len([r for r in all_results if r.get('status') in ['processed', 'info_only']])}/{len(expanded_urls)}")
    print(f"   â€¢ Downloads successful: {total_success}/{total_processed}")
    print(f"   â€¢ Session UUID: {session_uuid}")
    print(f"   â€¢ Base directory: {base_downloads_dir}")
    
    # Show failed videos if any
    failed_videos = [r for r in all_results if r.get("status") == "error"]
    if failed_videos:
        print(f"\nâŒ Failed videos ({len(failed_videos)}):")
        for failure in failed_videos:
            print(f"   â€¢ {failure.get('url')}: {failure.get('error')}")
    
    print(f"\nâœ… Batch processing completed!")
    print(f"ðŸ“ Structure: {base_downloads_dir}/{session_uuid}/[video_uuids]/[audio|video|transcripts]/")


def expand_url(url: str, max_videos: int = None, playlist_start: int = 1, playlist_end: int = None) -> list:
    """Expand a URL into individual video URLs, handling playlists."""
    from .core import get_video_info
    
    try:
        # Configure yt-dlp for playlist handling
        ydl_opts = {
            'quiet': True,
            'skip_download': True,
            'extract_flat': True,  # Only get URLs, don't extract full info
            'playliststart': playlist_start,
        }
        
        if playlist_end:
            ydl_opts['playlistend'] = playlist_end
        if max_videos:
            # Fix: Ensure all-integer math to avoid type issues
            calculated_end = playlist_start + max_videos - 1
            if playlist_end is not None:
                ydl_opts['playlistend'] = min(playlist_end, calculated_end)
            else:
                ydl_opts['playlistend'] = calculated_end
        
        from yt_dlp import YoutubeDL
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Check if it's a playlist
            if 'entries' in info and info['entries']:
                entries = info['entries']
                urls = []
                
                print(f"ðŸ“‹ Detected playlist: {info.get('title', 'Unknown playlist')}")
                print(f"   â€¢ Total videos: {len(entries)}")
                print(f"   â€¢ Processing range: {playlist_start} to {min(len(entries), playlist_end or len(entries))}")
                
                for entry in entries:
                    if entry and entry.get('url'):
                        urls.append(entry['url'])
                    elif entry and entry.get('id'):
                        urls.append(f"https://www.youtube.com/watch?v={entry['id']}")
                
                print(f"   â€¢ Expanded to {len(urls)} video URLs")
                return urls
            else:
                # Single video
                return [url]
                
    except Exception as e:
        print(f"âš ï¸ Could not expand URL {url}: {str(e)}")
        return [url]  # Return as-is if expansion fails


if __name__ == "__main__":
    main()