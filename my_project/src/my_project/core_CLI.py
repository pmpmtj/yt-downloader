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
    print_basic_info,
    print_audio_formats,
    print_video_formats,
    print_and_select_default_transcript,
    print_transcript_preview,
    list_transcript_metadata
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
        from .utils.path_utils import load_config
        config = load_config()
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
                print(f"🔄 No more audio formats to try (attempt {attempt + 1})")
                continue
                
            format_id = selected_format.get("format_id")
            print(f"🔄 Audio format attempt {attempt + 1}: {format_id} - {selected_format.get('format_note')}")
            
            # Try download with this format
            success = download_audio(url, format_id, save_path, max_retries, retry_delay)
            if success:
                return True
                
        except Exception as e:
            print(f"❌ Audio format {attempt + 1} failed: {str(e)}")
            continue
    
    return False


def download_video_with_fallback(url: str, video_formats: list, save_path: str, max_format_attempts: int = 3) -> bool:
    """Download video with format fallback on failure."""
    from .core import smart_video_selection
    
    try:
        from .utils.path_utils import load_config
        config = load_config()
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
                print(f"🔄 No more video formats to try (attempt {attempt + 1})")
                continue
                
            format_id = selected_format.get("format_id")
            print(f"🔄 Video format attempt {attempt + 1}: {format_id} - {selected_format.get('format_note')} - {selected_format.get('height')}p")
            
            # Try download with this format
            success = download_video(url, format_id, save_path, max_retries, retry_delay)
            if success:
                return True
                
        except Exception as e:
            print(f"❌ Video format {attempt + 1} failed: {str(e)}")
            continue
    
    return False

def parse_args(args=None):
    parser = argparse.ArgumentParser(
        description="YouTube Downloader CLI — select language, quality, media types"
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

    return parser.parse_args(args)


def process_single_video(url: str, session_uuid: str, base_downloads_dir: str, args) -> dict:
    """Process a single video URL and return results."""
    try:
        print(f"\n{'='*60}")
        print(f"Processing: {url}")
        print(f"{'='*60}")
        
        # Step 1: Fetch video info
        info = get_video_info(url)
        if info is None:
            print("❌ Failed to extract video information. Video may be private, deleted, or URL is invalid.")
            return {"status": "error", "error": "Failed to extract video info", "video_id": None, "title": None}
        
        print_basic_info(info)
        formats = info.get("formats", [])

        # Step 2: Generate video UUID for this specific video
        video_uuid = generate_video_uuid()
        print(f"Video UUID: {video_uuid}")

        # Step 3: Select defaults with quality override from CLI
        default_audio, audio_list = select_default_audio(formats, quality_override=args.quality)
        default_video, video_list = select_default_video(formats, quality_override=args.quality)
        default_combined, combined_list = select_combined_video_audio(formats, quality_override=args.quality) if args.video_with_audio else (None, [])
        default_transcript = print_and_select_default_transcript(info.get("id"), preferred_language=args.lang)
        
        # Show transcript preview if requested
        if args.preview_transcript and default_transcript:
            print_transcript_preview(info.get("id"), default_transcript.get("language_code"))

        # Step 4: Print info if requested
        if args.info_only or not (args.audio or args.video_only or args.video_with_audio or args.transcript):
            print_audio_formats(audio_list, default_audio)
            print_video_formats(video_list, default_video)
            if combined_list:
                print_video_formats(combined_list, default_combined)  # Combined formats display as video formats
            print("\n=== Defaults Selected ===")
            if default_audio:
                print(f"Default audio: [{default_audio.get('format_id')}] {default_audio.get('ext')} | {default_audio.get('format_note')}")
            if default_video:
                print(f"Default video: [{default_video.get('format_id')}] {default_video.get('ext')} | {default_video.get('format_note')}")
            if default_combined:
                print(f"Default video+audio: [{default_combined.get('format_id')}] {default_combined.get('ext')} | {default_combined.get('format_note')} | {default_combined.get('height')}p")
            if default_transcript:
                print(f"Default transcript language: {default_transcript.get('language')}")
            
            print(f"\nWould download to structure: {base_downloads_dir}/{session_uuid}/{video_uuid}/[audio|video|video_with_audio|transcripts]/")
            return {"status": "info_only", "video_id": info.get("id"), "title": info.get("title")}

        # Step 5: Downloads with error handling
        success_count = 0
        total_requested = sum([
            bool(args.audio and default_audio), 
            bool(args.video_only and default_video), 
            bool(args.video_with_audio and default_combined),
            bool(args.transcript and default_transcript)
        ])
        
        results = {"status": "processed", "video_id": info.get("id"), "title": info.get("title"), "success_count": 0, "total_requested": total_requested}
        
        if args.audio and default_audio:
            try:
                audio_dir = create_download_structure(base_downloads_dir, session_uuid, video_uuid, "audio")
                template = get_filename_template()
                filename = os.path.join(str(audio_dir), template)
                print(f"\nDownloading audio to: {audio_dir}/{template}")
                
                if download_audio_with_fallback(url, audio_list, filename):
                    success_count += 1
                    print(f"✅ Audio download completed successfully")
                else:
                    print(f"❌ Audio download failed after all fallback attempts")
            except Exception as e:
                print(f"💥 Audio download error: {str(e)}")

        if args.video_only and default_video:
            try:
                video_dir = create_download_structure(base_downloads_dir, session_uuid, video_uuid, "video")
                template = get_filename_template()
                filename = os.path.join(str(video_dir), template)
                print(f"\nDownloading video to: {video_dir}/{template}")
                
                if download_video_with_fallback(url, video_list, filename):
                    success_count += 1
                    print(f"✅ Video download completed successfully")
                else:
                    print(f"❌ Video download failed after all fallback attempts")
            except Exception as e:
                print(f"💥 Video download error: {str(e)}")

        if args.video_with_audio and default_combined:
            try:
                video_audio_dir = create_download_structure(base_downloads_dir, session_uuid, video_uuid, "video_with_audio")
                template = get_filename_template()
                filename = os.path.join(str(video_audio_dir), template)
                print(f"\nDownloading video+audio to: {video_audio_dir}/{template}")
                
                # Use the intelligent video+audio downloader with quality preference
                quality_pref = args.quality or "720p"
                if download_video_with_audio(url, quality_pref, filename):
                    success_count += 1
                    print(f"✅ Video+audio download completed successfully")
                else:
                    print(f"❌ Video+audio download failed after all attempts")
            except Exception as e:
                print(f"💥 Video+audio download error: {str(e)}")

        if args.transcript and default_transcript:
            try:
                transcripts_dir = create_download_structure(base_downloads_dir, session_uuid, video_uuid, "transcripts")
                base_transcript_path = os.path.join(str(transcripts_dir), f"{info.get('id')}_{default_transcript.get('language_code')}")
                
                # Determine formats to generate
                transcript_formats = []
                if args.transcript_formats:
                    if "all" in args.transcript_formats:
                        transcript_formats = ["clean", "timestamped", "structured"]
                    else:
                        transcript_formats = args.transcript_formats
                else:
                    # Default to all formats when using new system
                    try:
                        from .utils.path_utils import load_config
                        config = load_config()
                        format_config = config.get("transcripts", {}).get("processing", {}).get("output_formats", {})
                        transcript_formats = [fmt for fmt, enabled in format_config.items() if enabled]
                        if not transcript_formats:
                            transcript_formats = ["timestamped"]  # Fallback
                    except:
                        transcript_formats = ["timestamped"]  # Safe fallback
                
                print(f"\nSaving transcript formats: {', '.join(transcript_formats)}")
                print(f"Base path: {base_transcript_path}")
                
                try:
                    from .utils.path_utils import load_config
                    config = load_config()
                    network_config = config.get("network", {})
                    max_retries = network_config.get("max_retries", 3)
                    retry_delay = network_config.get("retry_delay_seconds", 2)
                except:
                    max_retries, retry_delay = 3, 2
                    
                result = download_transcript(
                    info.get("id"), 
                    default_transcript.get("language_code"), 
                    save_path=base_transcript_path, 
                    max_retries=max_retries, 
                    retry_delay=retry_delay,
                    formats=transcript_formats,
                    video_metadata=info
                )
                
                if result:
                    success_count += 1
                    if isinstance(result, dict):
                        print(f"✅ Transcript download completed successfully: {len(result)} formats saved")
                        for format_name, file_path in result.items():
                            print(f"   📄 {format_name}: {file_path}")
                    else:
                        print(f"✅ Transcript download completed successfully: {result}")
                else:
                    print(f"❌ Transcript download failed")
            except Exception as e:
                print(f"💥 Transcript download error: {str(e)}")
        
        # 🆕 Handle metadata export if requested (independent of transcript success)
        if args.metadata_export:
            try:
                from .metadata_exporter import export_metadata
                from .metadata_collector import collect_comprehensive_metadata
                from .utils.path_utils import load_config
                from pathlib import Path
                from youtube_transcript_api import YouTubeTranscriptApi
                
                config = load_config()
                if config.get("metadata_collection", {}).get("enabled", True):
                    print(f"📊 Exporting metadata to {args.metadata_export} format...")
                    
                    # Robust transcript data fetching with multiple fallback strategies
                    transcript_data = []
                    video_id = info.get("id")
                    
                    if video_id:
                        try:
                            # Strategy 1: Use selected transcript language if available
                            if default_transcript and default_transcript.get("language_code"):
                                transcript_data = YouTubeTranscriptApi.get_transcript(
                                    video_id, 
                                    languages=[default_transcript.get("language_code")]
                                )
                                print(f"✅ Fetched transcript in {default_transcript.get('language')} for metadata analysis")
                        except Exception as e:
                            logger.debug(f"Failed to fetch selected transcript language: {e}")
                            
                            try:
                                # Strategy 2: Try to get any available transcript
                                transcript_list = YouTubeTranscriptApi.list(video_id)
                                if transcript_list:
                                    # Prefer manual transcripts over auto-generated
                                    manual_transcripts = [t for t in transcript_list if not t.is_generated]
                                    auto_transcripts = [t for t in transcript_list if t.is_generated]
                                    
                                    # Try manual transcripts first
                                    target_transcript = None
                                    if manual_transcripts:
                                        target_transcript = manual_transcripts[0]
                                        print(f"✅ Using manual transcript in {target_transcript.language} for metadata analysis")
                                    elif auto_transcripts:
                                        target_transcript = auto_transcripts[0]
                                        print(f"✅ Using auto-generated transcript in {target_transcript.language} for metadata analysis")
                                    
                                    if target_transcript:
                                        transcript_data = target_transcript.fetch()
                                        
                            except Exception as e2:
                                logger.debug(f"Failed to fetch any transcript: {e2}")
                                print(f"⚠️ No transcript available for metadata analysis - proceeding with video-only metadata")
                    
                    # Collect comprehensive metadata (works even without transcript)
                    comprehensive_metadata = collect_comprehensive_metadata(info, transcript_data, config)
                    
                    # Generate robust export path (independent of transcript downloads)
                    if args.transcript and 'transcripts_dir' in locals():
                        # Use transcript directory if available
                        export_base_dir = str(transcripts_dir)
                    else:
                        # Create independent metadata export directory
                        metadata_dir = create_download_structure(base_downloads_dir, session_uuid, video_uuid, "metadata")
                        export_base_dir = str(metadata_dir)
                    
                    base_name = os.path.join(
                        export_base_dir, 
                        f"{info.get('id', 'unknown')}_metadata"
                    )
                    
                    export_path = export_metadata(
                        comprehensive_metadata, 
                        args.metadata_export, 
                        Path(base_name)
                    )
                    
                    if export_path:
                        print(f"✅ Metadata exported successfully: {export_path}")
                        success_count += 1  # Count successful metadata export
                    else:
                        print(f"❌ Metadata export failed")
                else:
                    print(f"⚠️ Metadata collection is disabled in configuration")
            except Exception as e:
                print(f"💥 Metadata export error: {str(e)}")
                logger.error(f"Metadata export failed for {url}: {e}")
        
        results["success_count"] = success_count
        print(f"\n📊 Video Summary: {success_count}/{total_requested} successful")
        return results
        
    except Exception as e:
        print(f"💥 Error processing video {url}: {str(e)}")
        return {"status": "error", "url": url, "error": str(e)}


def main():
    args = parse_args()
    
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
                print(f"📁 Loaded {len(batch_urls)} URLs from batch file: {args.batch_file}")
        except Exception as e:
            print(f"❌ Error reading batch file {args.batch_file}: {str(e)}")
            return
    
    if not urls_to_process:
        print("❌ No URLs provided to process")
        return
    
    # Step 2: Expand playlists and validate URLs
    expanded_urls = []
    for url in urls_to_process:
        try:
            expanded = expand_url(url, args.max_videos, args.playlist_start, args.playlist_end)
            expanded_urls.extend(expanded)
        except Exception as e:
            print(f"⚠️ Error expanding URL {url}: {str(e)}")
            expanded_urls.append(url)  # Add as-is if expansion fails
    
    print(f"\n🎯 Total videos to process: {len(expanded_urls)}")
    
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
        print(f"\n🎬 Processing video {i}/{len(expanded_urls)}")
        result = process_single_video(url, session_uuid, base_downloads_dir, args)
        all_results.append(result)
        
        if result.get("status") == "processed":
            total_success += result.get("success_count", 0)
            total_processed += result.get("total_requested", 0)
    
    # Step 5: Final summary
    print(f"\n{'='*80}")
    print(f"🎯 BATCH PROCESSING COMPLETE")
    print(f"{'='*80}")
    print(f"📊 Overall Summary:")
    print(f"   • Videos processed: {len([r for r in all_results if r.get('status') in ['processed', 'info_only']])}/{len(expanded_urls)}")
    print(f"   • Downloads successful: {total_success}/{total_processed}")
    print(f"   • Session UUID: {session_uuid}")
    print(f"   • Base directory: {base_downloads_dir}")
    
    # Show failed videos if any
    failed_videos = [r for r in all_results if r.get("status") == "error"]
    if failed_videos:
        print(f"\n❌ Failed videos ({len(failed_videos)}):")
        for failure in failed_videos:
            print(f"   • {failure.get('url')}: {failure.get('error')}")
    
    print(f"\n✅ Batch processing completed!")
    print(f"📁 Structure: {base_downloads_dir}/{session_uuid}/[video_uuids]/[audio|video|transcripts]/")


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
            ydl_opts['playlistend'] = min(playlist_end or float('inf'), playlist_start + max_videos - 1)
        
        from yt_dlp import YoutubeDL
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Check if it's a playlist
            if 'entries' in info and info['entries']:
                entries = info['entries']
                urls = []
                
                print(f"📋 Detected playlist: {info.get('title', 'Unknown playlist')}")
                print(f"   • Total videos: {len(entries)}")
                print(f"   • Processing range: {playlist_start} to {min(len(entries), playlist_end or len(entries))}")
                
                for entry in entries:
                    if entry and entry.get('url'):
                        urls.append(entry['url'])
                    elif entry and entry.get('id'):
                        urls.append(f"https://www.youtube.com/watch?v={entry['id']}")
                
                print(f"   • Expanded to {len(urls)} video URLs")
                return urls
            else:
                # Single video
                return [url]
                
    except Exception as e:
        print(f"⚠️ Could not expand URL {url}: {str(e)}")
        return [url]  # Return as-is if expansion fails


if __name__ == "__main__":
    main()
