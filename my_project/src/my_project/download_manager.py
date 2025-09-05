# download_manager.py
"""
download_manager.py

Database-aware download manager that integrates the existing download 
functionality with database logging and session management.
"""

from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
import datetime
import traceback

# Import existing core functionality
from .core import (
    get_video_info, select_default_audio, select_default_video,
    select_combined_video_audio, print_and_select_default_transcript,
    select_combined_with_lang, select_video_plus_audio_with_lang,
    build_format_string, _lang_matches, _fmt_audio_lang
)
from .yt_downloads_utils import (
    download_audio, download_video, download_video_with_audio,
    download_transcript, get_filename_template
)
from .utils.path_utils import (
    create_download_structure, load_normalized_config
)

# Import database functionality
from .db.db_port import get_db_port_from_env

# Import logging
from .logger_utils.logger_utils import setup_logger

# Setup logger for this module
logger = setup_logger("download_manager")


class DownloadManager:
    """Database-aware download manager that logs all operations."""
    
    def __init__(self):
        """Initialize download manager with database connection."""
        try:
            self.db = get_db_port_from_env()
            logger.info("Database connection established")
        except Exception as e:
            logger.error(f"Failed to initialize database connection: {e}")
            self.db = None
    
    def safe_db_operation(self, operation_name: str, fn, *args, **kwargs):
        """Safely execute database operation with error handling."""
        if not self.db:
            logger.warning(f"[DB SKIP] {operation_name} - no database connection")
            return None
        
        try:
            result = fn(*args, **kwargs)
            logger.debug(f"[DB OK] {operation_name}")
            return result
        except Exception as e:
            logger.warning(f"[DB WARN] {operation_name}: {e}")
            return None
    
    def check_existing_media_file(self, user_id: str, video_uuid: str, kind: str, 
                                 language_code: Optional[str], ext: str) -> Optional[Dict]:
        """Check if a media file of the same variant already exists in the database."""
        return self.safe_db_operation("check_existing_media_file", self.db.check_existing_media_file,
                                     user_id, video_uuid, kind, language_code, ext)
    
    def verify_file_exists(self, file_path: str) -> bool:
        """Verify that a file still exists on disk and is readable."""
        try:
            path_obj = Path(file_path)
            if not path_obj.exists():
                logger.debug(f"[DEDUP] File does not exist on disk: {file_path}")
                return False
            
            # Check if file is readable and has content
            if path_obj.stat().st_size == 0:
                logger.debug(f"[DEDUP] File is empty: {file_path}")
                return False
                
            logger.debug(f"[DEDUP] File exists and is valid: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"[DEDUP] Error verifying file: {file_path} - {str(e)}")
            return False
    
    def run_download_with_db(self, url: str, session_uuid: str, base_downloads_dir: str, 
                           download_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main download function with full database integration.
        
        Args:
            url: YouTube video URL
            session_uuid: Session identifier
            base_downloads_dir: Base directory for downloads  
            download_config: Configuration dict with download options
        
        Returns:
            Dictionary with download results and status
        """
        logger.info(f"Starting database-aware download for: {url}")
        
        # Extract download configuration
        args = download_config
        
        # Step 1: Initialize database session
        uid = self.safe_db_operation("ensure_anonymous_user", self.db.ensure_anonymous_user)
        
        # Prepare normalized config for session
        try:
            normalized_config = load_normalized_config()
            # Add runtime arguments to config
            normalized_config.update({
                'runtime_args': {
                    'audio': args.get('audio', False),
                    'video_only': args.get('video_only', False), 
                    'video_with_audio': args.get('video_with_audio', False),
                    'transcript': args.get('transcript', False),
                    'quality': args.get('quality'),
                    'lang': args.get('lang'),
                    'audio_lang': args.get('audio_lang', []),
                    'require_audio_lang': args.get('require_audio_lang', False)
                }
            })
        except Exception as e:
            logger.warning(f"Could not load config for session: {e}")
            normalized_config = {'runtime_args': args}
        
        sid = self.safe_db_operation("begin_session", self.db.begin_session, uid, normalized_config)
        
        # Determine what types of content to download
        download_types = []
        if args.get('audio'): download_types.append('audio')
        if args.get('video_only'): download_types.append('video')
        if args.get('video_with_audio'): download_types.append('video_with_audio')
        if args.get('transcript'): download_types.append('transcript')
        
        if not download_types:
            download_types = ['info_only']
        
        jid = self.safe_db_operation("create_job", self.db.create_job, uid, sid, url, download_types)
        
        try:
            # Step 2: Fetch video info
            logger.debug(f"Fetching video info for {url}")
            info = get_video_info(url)
            if info is None:
                error_msg = "Failed to extract video information"
                self.safe_db_operation("update_job", self.db.update_job, 
                                     jid, status='failed', last_error=error_msg, tries_inc=1)
                self.safe_db_operation("log_event", self.db.log_event, 
                                     uid, None, jid, 'ERROR', {'error': error_msg})
                return {"status": "error", "error": error_msg, "video_id": None, "title": None}
            
            # Log successful info fetch
            vid = self.safe_db_operation("upsert_video", self.db.upsert_video, 
                                       uid, info['id'], info.get('title'), info)
            self.safe_db_operation("log_event", self.db.log_event, 
                                 uid, vid, jid, 'INFO_FETCHED', {'id': info['id']})
            
            # Step 3: Use video UUID from database (for proper deduplication)
            video_uuid = vid  # Use the video_uuid returned by upsert_video for deduplication
            logger.debug(f"Using video UUID from database: {video_uuid}")
            
            # Step 4: Process downloads
            results = self._process_downloads(
                url, info, video_uuid, session_uuid, base_downloads_dir, 
                args, uid, vid, jid
            )
            
            # Step 5: Update job status
            if results.get('success_count', 0) > 0:
                self.safe_db_operation("update_job", self.db.update_job, 
                                     jid, status='succeeded', progress=100, message='OK')
                logger.info(f"Download job completed successfully: {results['success_count']}/{results['total_requested']}")
            else:
                self.safe_db_operation("update_job", self.db.update_job, 
                                     jid, status='failed', last_error='No downloads succeeded', tries_inc=1)
            
            return results
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Download failed: {error_msg}")
            logger.debug(f"Full traceback: {traceback.format_exc()}")
            
            self.safe_db_operation("update_job", self.db.update_job, 
                                 jid, status='failed', last_error=error_msg, tries_inc=1)
            self.safe_db_operation("log_event", self.db.log_event, 
                                 uid, vid if 'vid' in locals() else None, jid, 'ERROR', {'error': error_msg})
            raise
        
        finally:
            # Always clean up session
            self.safe_db_operation("end_session", self.db.end_session, sid)
            logger.debug("Database session ended")
    
    def _process_downloads(self, url: str, info: Dict, video_uuid: str, session_uuid: str, 
                          base_downloads_dir: str, args: Dict, uid, vid, jid) -> Dict[str, Any]:
        """Process individual downloads with database logging."""
        formats = info.get("formats", [])
        success_count = 0
        total_requested = sum([
            bool(args.get('audio')), 
            bool(args.get('video_only')), 
            bool(args.get('video_with_audio')),
            bool(args.get('transcript'))
        ])
        
        results = {
            "status": "processed", 
            "video_id": info.get("id"), 
            "title": info.get("title"),
            "success_count": 0, 
            "total_requested": total_requested
        }
        
        # Process audio download
        if args.get('audio'):
            logger.debug("Processing audio download with database logging")
            try:
                success = self._download_audio_with_db(
                    url, formats, video_uuid, session_uuid, base_downloads_dir, 
                    args, uid, vid, jid, info
                )
                if success:
                    success_count += 1
                    logger.info("Ã¢Å“â€¦ Audio download completed successfully")
                else:
                    logger.warning("Ã¢ÂÅ’ Audio download failed")
            except Exception as e:
                logger.error(f"Ã°Å¸â€™Â¥ Audio download error: {str(e)}")
        
        # Process video-only download
        if args.get('video_only'):
            logger.debug("Processing video-only download with database logging")
            try:
                success = self._download_video_with_db(
                    url, formats, video_uuid, session_uuid, base_downloads_dir,
                    args, uid, vid, jid, info
                )
                if success:
                    success_count += 1
                    logger.info("Ã¢Å“â€¦ Video download completed successfully")
                else:
                    logger.warning("Ã¢ÂÅ’ Video download failed")
            except Exception as e:
                logger.error(f"Ã°Å¸â€™Â¥ Video download error: {str(e)}")
        
        # Process video+audio download  
        if args.get('video_with_audio'):
            logger.debug("Processing video+audio download with database logging")
            try:
                success = self._download_video_audio_with_db(
                    url, formats, video_uuid, session_uuid, base_downloads_dir,
                    args, uid, vid, jid, info
                )
                if success:
                    success_count += 1
                    logger.info("Ã¢Å“â€¦ Video+audio download completed successfully") 
                else:
                    logger.warning("Ã¢ÂÅ’ Video+audio download failed")
            except Exception as e:
                logger.error(f"Ã°Å¸â€™Â¥ Video+audio download error: {str(e)}")
        
        # Process transcript download
        if args.get('transcript'):
            logger.debug("Processing transcript download with database logging")
            try:
                success = self._download_transcript_with_db(
                    info, video_uuid, session_uuid, base_downloads_dir,
                    args, uid, vid, jid
                )
                if success:
                    success_count += 1
                    logger.info("Ã¢Å“â€¦ Transcript download completed successfully")
                else:
                    logger.warning("Ã¢ÂÅ’ Transcript download failed")
            except Exception as e:
                logger.error(f"Ã°Å¸â€™Â¥ Transcript download error: {str(e)}")
        
        results["success_count"] = success_count
        logger.info(f"Ã°Å¸â€œÅ  Downloads completed: {success_count}/{total_requested}")
        return results
    
    def _download_audio_with_db(self, url: str, formats: List, video_uuid: str, 
                               session_uuid: str, base_downloads_dir: str, 
                               args: Dict, uid, vid, jid, info: Dict) -> bool:
        """Download audio with database logging."""
        logger.debug("Starting audio download with database integration")
        
        # Select audio format
        default_audio, audio_list = select_default_audio(formats, quality_override=args.get('quality'))
        if not default_audio:
            error_msg = "No suitable audio format found"
            self.safe_db_operation("log_event", self.db.log_event, 
                                 uid, vid, jid, 'ERROR', {'error': error_msg, 'type': 'audio'})
            return False
        
        # Log format selection
        format_scores = {"quality_match": True, "format_preference": True}
        format_prefs = {"quality": args.get('quality'), "formats": ["mp3", "m4a"]}
        self.safe_db_operation("record_format_selection", self.db.record_format_selection,
                             uid, vid, 'audio', default_audio.get('format_id'), format_scores, format_prefs)
        
        # Check for existing media file before downloading
        ext = default_audio.get('ext', 'mp3')
        existing_file = self.check_existing_media_file(uid, vid, 'audio', None, ext)
        
        if existing_file:
            logger.info(f"[DEDUP] Found existing audio file in database: {existing_file['filename']}")
            if self.verify_file_exists(existing_file['path']):
                logger.info(f"[DEDUP] âœ… Skipping audio download - file already exists: {existing_file['path']}")
                # Log the skip event
                self.safe_db_operation("log_event", self.db.log_event,
                                     uid, vid, jid, 'DOWNLOAD_SKIPPED',
                                     {'reason': 'duplicate_exists', 'existing_file_id': existing_file['id'], 
                                      'path': existing_file['path'], 'type': 'audio'})
                return True  # Return success since we have the file
            else:
                logger.warning(f"[DEDUP] âš ï¸ Database has existing record but file not found at old path: {existing_file['path']}")
                
                # Check if we can find the file anywhere in the downloads directory using the filename
                base_downloads = Path(base_downloads_dir)
                search_pattern = f"**/{existing_file['filename']}"
                matching_files = list(base_downloads.glob(search_pattern))
                
                if matching_files:
                    # Found the file in another location
                    found_file = matching_files[0]  # Use the first match
                    logger.info(f"[DEDUP] âœ… Found existing file in different location: {found_file}")
                    logger.info(f"[DEDUP] âœ… Skipping audio download - file already exists elsewhere")
                    
                    # Log the skip event with the found path
                    self.safe_db_operation("log_event", self.db.log_event,
                                         uid, vid, jid, 'DOWNLOAD_SKIPPED',
                                         {'reason': 'duplicate_exists_different_path', 'existing_file_id': existing_file['id'], 
                                          'old_path': existing_file['path'], 'found_path': str(found_file), 'type': 'audio'})
                    return True  # Return success since we have the file
                else:
                    logger.warning(f"[DEDUP] âš ï¸ File not found anywhere in downloads directory - proceeding with download")
                    # Continue with download since file is truly missing
        
        # Setup download path
        audio_dir = create_download_structure(base_downloads_dir, session_uuid, video_uuid, "audio")
        template = get_filename_template()
        
        # Render filename template with actual video info
        title = info.get('title', 'video')
        vid_id = info.get('id', '')
        rendered_filename = template.replace('%(title)s', title).replace('%(id)s', vid_id).replace('%(ext)s', ext)
        filename = str(audio_dir / rendered_filename)
        
        logger.debug(f"Audio download path: {filename}")
        logger.debug(f"[FILENAME-DEBUG] Template: {template}")
        logger.debug(f"[FILENAME-DEBUG] Rendered: {rendered_filename}")
        logger.debug(f"[FILENAME-DEBUG] Full path: {filename}")
        
        # Perform download
        try:
            from .core_CLI import download_audio_with_fallback
            success = download_audio_with_fallback(url, audio_list, filename)
            
            if success:
                # Record successful download in database
                file_path = Path(filename)
                logger.debug(f"[MEDIAFILE-DEBUG] Checking file existence: {file_path}")
                logger.debug(f"[MEDIAFILE-DEBUG] File exists: {file_path.exists()}")
                
                if file_path.exists():
                    file_size = file_path.stat().st_size
                    file_name = file_path.name
                    
                    logger.debug(f"[MEDIAFILE-DEBUG] Registering media_file: user_id={uid}, video_uuid={vid}, kind=audio, path={str(file_path)}, filename={file_name}, ext={default_audio.get('ext', 'unknown')}, size_bytes={file_size}")
                    mid = self.safe_db_operation("record_media_file", self.db.record_media_file,
                                               uid, vid, 'audio', None, str(file_path), file_name, 
                                               default_audio.get('ext', 'unknown'), file_size)
                    logger.debug(f"[MEDIAFILE-DEBUG] record_media_file returned id: {mid}")
                    
                    self.safe_db_operation("log_event", self.db.log_event,
                                         uid, vid, jid, 'DOWNLOAD_COMPLETED', 
                                         {'path': str(file_path), 'type': 'audio', 'format_id': default_audio.get('format_id')})
                    logger.debug(f"Audio download logged in database: {file_path}")
                else:
                    logger.warning(f"[MEDIAFILE-DEBUG] File does not exist after download: {file_path}")
            
            return success
            
        except Exception as e:
            error_msg = f"Audio download failed: {str(e)}"
            self.safe_db_operation("log_event", self.db.log_event,
                                 uid, vid, jid, 'ERROR', {'error': error_msg, 'type': 'audio'})
            logger.error(error_msg)
            return False
    
    def _download_video_with_db(self, url: str, formats: List, video_uuid: str,
                               session_uuid: str, base_downloads_dir: str,
                               args: Dict, uid, vid, jid, info: Dict) -> bool:
        """Download video-only with database logging."""
        logger.debug("Starting video-only download with database integration")
        
        # Select video format
        default_video, video_list = select_default_video(formats, quality_override=args.get('quality'))
        if not default_video:
            error_msg = "No suitable video format found"
            self.safe_db_operation("log_event", self.db.log_event,
                                 uid, vid, jid, 'ERROR', {'error': error_msg, 'type': 'video'})
            return False
        
        # Log format selection
        format_scores = {"quality_match": True, "format_preference": True}
        format_prefs = {"quality": args.get('quality'), "formats": ["mp4", "webm"]}
        self.safe_db_operation("record_format_selection", self.db.record_format_selection,
                             uid, vid, 'video', default_video.get('format_id'), format_scores, format_prefs)
        
        # Check for existing media file before downloading
        ext = default_video.get('ext', 'mp4')
        existing_file = self.check_existing_media_file(uid, vid, 'video', None, ext)
        
        if existing_file:
            logger.info(f"[DEDUP] Found existing video file in database: {existing_file['filename']}")
            if self.verify_file_exists(existing_file['path']):
                logger.info(f"[DEDUP] âœ… Skipping video download - file already exists: {existing_file['path']}")
                # Log the skip event
                self.safe_db_operation("log_event", self.db.log_event,
                                     uid, vid, jid, 'DOWNLOAD_SKIPPED',
                                     {'reason': 'duplicate_exists', 'existing_file_id': existing_file['id'], 
                                      'path': existing_file['path'], 'type': 'video'})
                return True  # Return success since we have the file
            else:
                logger.warning(f"[DEDUP] âš ï¸ Database has existing record but file not found at old path: {existing_file['path']}")
                
                # Check if we can find the file anywhere in the downloads directory using the filename
                base_downloads = Path(base_downloads_dir)
                search_pattern = f"**/{existing_file['filename']}"
                matching_files = list(base_downloads.glob(search_pattern))
                
                if matching_files:
                    # Found the file in another location
                    found_file = matching_files[0]  # Use the first match
                    logger.info(f"[DEDUP] âœ… Found existing file in different location: {found_file}")
                    logger.info(f"[DEDUP] âœ… Skipping video download - file already exists elsewhere")
                    
                    # Log the skip event with the found path
                    self.safe_db_operation("log_event", self.db.log_event,
                                         uid, vid, jid, 'DOWNLOAD_SKIPPED',
                                         {'reason': 'duplicate_exists_different_path', 'existing_file_id': existing_file['id'], 
                                          'old_path': existing_file['path'], 'found_path': str(found_file), 'type': 'video'})
                    return True  # Return success since we have the file
                else:
                    logger.warning(f"[DEDUP] âš ï¸ File not found anywhere in downloads directory - proceeding with download")
                    # Continue with download since file is truly missing
        
        # Setup download path
        video_dir = create_download_structure(base_downloads_dir, session_uuid, video_uuid, "video")
        template = get_filename_template()
        
        # Render filename template with actual video info
        title = info.get('title', 'video')
        vid_id = info.get('id', '')
        rendered_filename = template.replace('%(title)s', title).replace('%(id)s', vid_id).replace('%(ext)s', ext)
        filename = str(video_dir / rendered_filename)
        
        logger.debug(f"Video download path: {filename}")
        logger.debug(f"[FILENAME-DEBUG] Template: {template}")
        logger.debug(f"[FILENAME-DEBUG] Rendered: {rendered_filename}")
        logger.debug(f"[FILENAME-DEBUG] Full path: {filename}")
        
        # Perform download
        try:
            from .core_CLI import download_video_with_fallback
            success = download_video_with_fallback(url, video_list, filename)
            
            if success:
                # Record successful download in database
                file_path = Path(filename)
                logger.debug(f"[MEDIAFILE-DEBUG] Checking file existence: {file_path}")
                logger.debug(f"[MEDIAFILE-DEBUG] File exists: {file_path.exists()}")
                
                if file_path.exists():
                    file_size = file_path.stat().st_size
                    file_name = file_path.name
                    
                    logger.debug(f"[MEDIAFILE-DEBUG] Registering media_file: user_id={uid}, video_uuid={vid}, kind=video, path={str(file_path)}, filename={file_name}, ext={default_video.get('ext', 'unknown')}, size_bytes={file_size}")
                    mid = self.safe_db_operation("record_media_file", self.db.record_media_file,
                                               uid, vid, 'video', None, str(file_path), file_name,
                                               default_video.get('ext', 'unknown'), file_size)
                    logger.debug(f"[MEDIAFILE-DEBUG] record_media_file returned id: {mid}")
                    
                    self.safe_db_operation("log_event", self.db.log_event,
                                         uid, vid, jid, 'DOWNLOAD_COMPLETED',
                                         {'path': str(file_path), 'type': 'video', 'format_id': default_video.get('format_id')})
                    logger.debug(f"Video download logged in database: {file_path}")
                else:
                    logger.warning(f"[MEDIAFILE-DEBUG] File does not exist after download: {file_path}")
            
            return success
            
        except Exception as e:
            error_msg = f"Video download failed: {str(e)}"
            self.safe_db_operation("log_event", self.db.log_event,
                                 uid, vid, jid, 'ERROR', {'error': error_msg, 'type': 'video'})
            logger.error(error_msg)
            return False
    
    def _download_video_audio_with_db(self, url: str, formats: List, video_uuid: str,
                                     session_uuid: str, base_downloads_dir: str,
                                     args: Dict, uid, vid, jid, info: Dict) -> bool:
        """Download video+audio with database logging."""
        logger.debug("Starting video+audio download with database integration")
        
        # Get language preferences
        preferred_langs = args.get('audio_lang', [])
        require_lang = args.get('require_audio_lang', False)
        
        if not preferred_langs:
            try:
                config = load_normalized_config()
                preferred_langs = config.get("quality_preferences", {}).get("audio", {}).get("preferred_languages", [])
                if not require_lang:
                    require_lang = config.get("quality_preferences", {}).get("audio", {}).get("require_language_match", False)
            except:
                pass
        
        # Setup download path
        video_audio_dir = create_download_structure(base_downloads_dir, session_uuid, video_uuid, "video_with_audio")
        template = get_filename_template()
        
        # Render filename template with actual video info
        title = info.get('title', 'video')
        vid_id = info.get('id', '')
        ext = 'mp4'  # Most video+audio downloads result in mp4
        rendered_filename = template.replace('%(title)s', title).replace('%(id)s', vid_id).replace('%(ext)s', ext)
        filename = str(video_audio_dir / rendered_filename)
        
        logger.debug(f"Video+audio download path: {filename}")
        logger.debug(f"[FILENAME-DEBUG] Template: {template}")
        logger.debug(f"[FILENAME-DEBUG] Rendered: {rendered_filename}")
        logger.debug(f"[FILENAME-DEBUG] Full path: {filename}")
        
        # Select format with language preferences
        selected_format = None
        format_method = "unknown"
        
        try:
            config = load_normalized_config()
            video_prefs = config.get("quality_preferences", {}).get("video", {})
            audio_prefs = config.get("quality_preferences", {}).get("audio", {})
        except:
            video_prefs = {}
            audio_prefs = {}
        
        if args.get('quality'):
            video_prefs = video_prefs.copy()
            video_prefs['preferred_quality'] = args.get('quality')
        
        if preferred_langs:
            logger.debug(f"Ã°Å¸Å½Âµ Preferred audio languages: {', '.join(preferred_langs)}")
            
            # Try combined formats with language filtering first
            selected_combined = select_combined_with_lang(formats, video_prefs, preferred_langs)
            
            if selected_combined and (not preferred_langs or _lang_matches(_fmt_audio_lang(selected_combined), preferred_langs)):
                selected_format = selected_combined.get('format_id')
                format_method = "combined_with_lang"
                
                # Log format selections
                format_scores = {"language_match": True, "quality_match": True}
                format_prefs = {"languages": preferred_langs, "quality": args.get('quality')}
                self.safe_db_operation("record_format_selection", self.db.record_format_selection,
                                     uid, vid, 'video_with_audio', selected_format, format_scores, format_prefs)
                
                logger.debug(f"Ã°Å¸â€œÂ¹ Using combined format: {selected_format} (language: {_fmt_audio_lang(selected_combined) or 'unknown'})")
            else:
                # Try separate video+audio with language matching
                video_fmt, audio_fmt = select_video_plus_audio_with_lang(formats, video_prefs, audio_prefs, preferred_langs)
                
                if video_fmt and audio_fmt and _lang_matches(_fmt_audio_lang(audio_fmt), preferred_langs):
                    selected_format = build_format_string(video_fmt, audio_fmt)
                    format_method = "separate_with_lang"
                    
                    # Log format selections for both video and audio
                    v_scores = {"quality_match": True, "format_preference": True}
                    v_prefs = {"quality": args.get('quality'), "formats": ["mp4", "webm"]}
                    a_scores = {"language_match": True, "quality_match": True}
                    a_prefs = {"languages": preferred_langs, "quality": args.get('quality')}
                    
                    self.safe_db_operation("record_format_selection", self.db.record_format_selection,
                                         uid, vid, 'video', video_fmt.get('format_id'), v_scores, v_prefs)
                    self.safe_db_operation("record_format_selection", self.db.record_format_selection,
                                         uid, vid, 'audio', audio_fmt.get('format_id'), a_scores, a_prefs)
                    
                    logger.debug(f"Ã°Å¸â€œÂ¹ Using separate streams: {selected_format} (audio language: {_fmt_audio_lang(audio_fmt) or 'unknown'})")
                elif require_lang:
                    error_msg = f"Requested audio language(s) {preferred_langs} not available for this video"
                    self.safe_db_operation("log_event", self.db.log_event,
                                         uid, vid, jid, 'ERROR', {'error': error_msg, 'type': 'video_with_audio'})
                    logger.error(error_msg)
                    return False
        
        # Fallback to best available if no language match or no preference
        if not selected_format:
            logger.debug("Ã¢Å¡Â Ã¯Â¸Â No language match found, falling back to best quality")
            default_combined, combined_list = select_combined_video_audio(formats, quality_override=args.get('quality'))
            if default_combined:
                selected_format = default_combined.get('format_id')
                format_method = "fallback_combined"
                
                # Log fallback format selection
                format_scores = {"quality_match": True, "fallback": True}
                format_prefs = {"quality": args.get('quality'), "fallback_reason": "no_language_match"}
                self.safe_db_operation("record_format_selection", self.db.record_format_selection,
                                     uid, vid, 'video_with_audio', selected_format, format_scores, format_prefs)
        
        if not selected_format:
            error_msg = "No suitable video+audio format found"
            self.safe_db_operation("log_event", self.db.log_event,
                                 uid, vid, jid, 'ERROR', {'error': error_msg, 'type': 'video_with_audio'})
            return False
        
        # Check for existing media file before downloading
        audio_lang = None
        if format_method in ["combined_with_lang", "separate_with_lang"] and preferred_langs:
            audio_lang = preferred_langs[0]  # Use first preferred language for checking
        
        existing_file = self.check_existing_media_file(uid, vid, 'video_with_audio', audio_lang, ext)
        
        if existing_file:
            logger.info(f"[DEDUP] Found existing video+audio file in database: {existing_file['filename']}")
            if self.verify_file_exists(existing_file['path']):
                logger.info(f"[DEDUP] âœ… Skipping video+audio download - file already exists: {existing_file['path']}")
                # Log the skip event
                self.safe_db_operation("log_event", self.db.log_event,
                                     uid, vid, jid, 'DOWNLOAD_SKIPPED',
                                     {'reason': 'duplicate_exists', 'existing_file_id': existing_file['id'], 
                                      'path': existing_file['path'], 'type': 'video_with_audio'})
                return True  # Return success since we have the file
            else:
                logger.warning(f"[DEDUP] âš ï¸ Database has existing record but file not found at old path: {existing_file['path']}")
                
                # Check if we can find the file anywhere in the downloads directory using the filename
                base_downloads = Path(base_downloads_dir)
                target_filename = existing_file['filename']
                
                logger.debug(f"[DEDUP] Searching for files in directory: {base_downloads}")
                logger.debug(f"[DEDUP] Looking for filename: {target_filename}")
                
                # Use iterative search instead of glob to avoid special character issues
                matching_files = []
                try:
                    for file_path in base_downloads.rglob("*"):
                        if file_path.is_file() and file_path.name == target_filename:
                            matching_files.append(file_path)
                except Exception as e:
                    logger.warning(f"[DEDUP] Error during file search: {e}")
                
                logger.debug(f"[DEDUP] Found {len(matching_files)} matching files: {[str(f) for f in matching_files]}")
                
                if matching_files:
                    # Found the file in another location
                    found_file = matching_files[0]  # Use the first match
                    logger.info(f"[DEDUP] âœ… Found existing file in different location: {found_file}")
                    logger.info(f"[DEDUP] âœ… Skipping video+audio download - file already exists elsewhere")
                    
                    # Log the skip event with the found path
                    self.safe_db_operation("log_event", self.db.log_event,
                                         uid, vid, jid, 'DOWNLOAD_SKIPPED',
                                         {'reason': 'duplicate_exists_different_path', 'existing_file_id': existing_file['id'], 
                                          'old_path': existing_file['path'], 'found_path': str(found_file), 'type': 'video_with_audio'})
                    return True  # Return success since we have the file
                else:
                    logger.warning(f"[DEDUP] âš ï¸ File not found anywhere in downloads directory - proceeding with download")
                    # Continue with download since file is truly missing
        
        # Perform download
        try:
            success = download_video_with_audio(url, args.get('quality') or "720p", filename, format_override=selected_format)
            
            if success:
                # Record successful download in database
                file_path = Path(filename)
                logger.debug(f"[MEDIAFILE-DEBUG] Checking file existence: {file_path}")
                logger.debug(f"[MEDIAFILE-DEBUG] File exists: {file_path.exists()}")
                
                # If the expected file doesn't exist, look for the yt-dlp sanitized version
                if not file_path.exists():
                    # yt-dlp sanitizes filenames differently, try to find the actual file
                    download_dir = file_path.parent
                    expected_filename = file_path.name
                    logger.debug(f"[MEDIAFILE-DEBUG] Expected file not found, searching in directory: {download_dir}")
                    
                    # Look for files with similar names (yt-dlp may have sanitized differently)
                    if download_dir.exists():
                        for actual_file in download_dir.iterdir():
                            if actual_file.is_file() and actual_file.suffix == '.mp4':
                                logger.debug(f"[MEDIAFILE-DEBUG] Found actual file: {actual_file.name}")
                                # Use the first mp4 file found (should be our download)
                                file_path = actual_file
                                break
                    
                    logger.debug(f"[MEDIAFILE-DEBUG] Using actual file path: {file_path}")
                    logger.debug(f"[MEDIAFILE-DEBUG] File exists now: {file_path.exists()}")
                
                if file_path.exists():
                    file_size = file_path.stat().st_size
                    file_name = file_path.name
                    
                    # Determine audio language for database record
                    audio_lang = None
                    if format_method in ["combined_with_lang", "separate_with_lang"] and preferred_langs:
                        audio_lang = preferred_langs[0]  # Use first preferred language as recorded language
                    
                    logger.debug(f"[MEDIAFILE-DEBUG] Registering media_file: user_id={uid}, video_uuid={vid}, kind=video_with_audio, path={str(file_path)}, filename={file_name}, ext=mp4, size_bytes={file_size}")
                    mid = self.safe_db_operation("record_media_file", self.db.record_media_file,
                                               uid, vid, 'video_with_audio', audio_lang, str(file_path), file_name,
                                               'mp4', file_size)  # Most video+audio downloads result in mp4
                    logger.debug(f"[MEDIAFILE-DEBUG] record_media_file returned id: {mid}")
                    
                    self.safe_db_operation("log_event", self.db.log_event,
                                         uid, vid, jid, 'DOWNLOAD_COMPLETED',
                                         {'path': str(file_path), 'type': 'video_with_audio', 'format_method': format_method, 'format_id': selected_format})
                    logger.debug(f"Video+audio download logged in database: {file_path}")
                else:
                    logger.warning(f"[MEDIAFILE-DEBUG] File does not exist after download: {file_path}")
            
            return success
            
        except Exception as e:
            error_msg = f"Video+audio download failed: {str(e)}"
            self.safe_db_operation("log_event", self.db.log_event,
                                 uid, vid, jid, 'ERROR', {'error': error_msg, 'type': 'video_with_audio'})
            logger.error(error_msg)
            return False
    
    def _download_transcript_with_db(self, info: Dict, video_uuid: str, session_uuid: str,
                                   base_downloads_dir: str, args: Dict, uid, vid, jid) -> bool:
        """Download transcript with database logging."""
        logger.debug("Starting transcript download with database integration")
        
        # Select transcript
        default_transcript = print_and_select_default_transcript(info.get("id"), preferred_language=args.get('lang'))
        if not default_transcript:
            error_msg = "No suitable transcript found"
            self.safe_db_operation("log_event", self.db.log_event,
                                 uid, vid, jid, 'ERROR', {'error': error_msg, 'type': 'transcript'})
            return False
        
        # Setup download path
        transcripts_dir = create_download_structure(base_downloads_dir, session_uuid, video_uuid, "transcripts")
        base_transcript_path = str(transcripts_dir / f"{info.get('id')}_{default_transcript.get('language_code')}")
        
        logger.debug(f"Transcript download path: {base_transcript_path}")
        
        # Determine formats to generate
        transcript_formats = []
        if args.get('transcript_formats'):
            if "all" in args.get('transcript_formats'):
                transcript_formats = ["clean", "timestamped", "structured"]
            else:
                transcript_formats = args.get('transcript_formats')
        else:
            try:
                config = load_normalized_config()
                transcript_formats = config.get("transcripts", {}).get("processing", {}).get("output_formats_list", [])
                if not transcript_formats:
                    format_config = config.get("transcripts", {}).get("processing", {}).get("output_formats", {})
                    transcript_formats = [fmt for fmt, enabled in format_config.items() if enabled]
                if not transcript_formats:
                    transcript_formats = ["timestamped"]
            except:
                transcript_formats = ["timestamped"]
        
        # Perform download
        try:
            try:
                config = load_normalized_config()
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
                # Record successful transcript download in database
                if isinstance(result, dict):
                    # Multiple formats downloaded
                    for format_name, file_path in result.items():
                        file_path_obj = Path(file_path)
                        if file_path_obj.exists():
                            file_size = file_path_obj.stat().st_size
                            
                            # Create media file record (transcript files are linked to the video)
                            mid = self.safe_db_operation("record_media_file", self.db.record_media_file,
                                                       uid, vid, 'transcript', default_transcript.get('language_code'),
                                                       str(file_path_obj), file_path_obj.name, format_name, file_size)
                            
                            # Record transcript specifically
                            self.safe_db_operation("record_transcript", self.db.record_transcript,
                                                 uid, vid, mid, str(file_path_obj), format_name)
                    
                    self.safe_db_operation("log_event", self.db.log_event,
                                         uid, vid, jid, 'DOWNLOAD_COMPLETED',
                                         {'type': 'transcript', 'formats': list(result.keys()), 'language': default_transcript.get('language_code')})
                    logger.debug(f"Transcript downloads logged in database: {len(result)} formats")
                else:
                    # Single format downloaded
                    file_path_obj = Path(result)
                    if file_path_obj.exists():
                        file_size = file_path_obj.stat().st_size
                        
                        mid = self.safe_db_operation("record_media_file", self.db.record_media_file,
                                                   uid, vid, 'transcript', default_transcript.get('language_code'),
                                                   str(file_path_obj), file_path_obj.name, 'transcript', file_size)
                        
                        self.safe_db_operation("record_transcript", self.db.record_transcript,
                                             uid, vid, mid, str(file_path_obj), None)
                    
                    self.safe_db_operation("log_event", self.db.log_event,
                                         uid, vid, jid, 'DOWNLOAD_COMPLETED',
                                         {'path': str(result), 'type': 'transcript', 'language': default_transcript.get('language_code')})
                    logger.debug(f"Transcript download logged in database: {result}")
            
            return bool(result)
            
        except Exception as e:
            error_msg = f"Transcript download failed: {str(e)}"
            self.safe_db_operation("log_event", self.db.log_event,
                                 uid, vid, jid, 'ERROR', {'error': error_msg, 'type': 'transcript'})
            logger.error(error_msg)
            return False


# Convenience function for backwards compatibility
def get_download_manager() -> DownloadManager:
    """Get a download manager instance."""
    return DownloadManager()