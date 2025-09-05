# db_port.py
from __future__ import annotations
import os, time, datetime
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional
from datetime import timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

from .models import (
    Base, PlatformUser, Session as DbSession, Job, Video, MediaFile,
    Event, Transcript, FormatSelection
)

ANON_EMAIL = 'anonymous@localhost'

class DbPort:
    """Interface for DB sideÃ¢â‚¬â€˜effects. Keep calls minimal and idempotent where possible."""
    def ensure_anonymous_user(self) -> str: ...
    def begin_session(self, user_id: str, effective_config: Dict[str, Any]) -> str: ...
    def end_session(self, session_uuid: str) -> None: ...

    def create_job(self, user_id: str, session_uuid: Optional[str], url: str, requested_types: Iterable[str]) -> str: ...
    def update_job(self, job_id: str, *, status: Optional[str] = None, progress: Optional[int] = None,
                   message: Optional[str] = None, last_error: Optional[str] = None, tries_inc: int = 0) -> None: ...

    def upsert_video(self, user_id: str, youtube_id: str, title: Optional[str], raw_info: Dict[str, Any]) -> str: ...
    def record_format_selection(self, user_id: str, video_uuid: str, selection_kind: str,
                                chosen_format_id: Optional[str], scores: Dict[str, Any],
                                preferences_snapshot: Dict[str, Any]) -> None: ...
    def record_media_file(self, user_id: str, video_uuid: str, kind: str, language_code: Optional[str],
                          path: str, filename: str, ext: str, size_bytes: Optional[int],
                          is_final: bool = True, status: str = 'completed') -> int: ...
    def mark_media_deleted(self, media_file_id: int, file_moved_to: Optional[str] = None) -> None: ...
    def check_existing_media_file(self, user_id: str, video_uuid: str, kind: str, 
                                 language_code: Optional[str], ext: str) -> Optional[Dict]: ...

    def log_event(self, user_id: str, video_uuid: Optional[str], job_id: Optional[str],
                  event_type: str, payload: Dict[str, Any]) -> None: ...

    def record_transcript(self, user_id: str, video_uuid: str, media_file_id: Optional[int],
                          path: str, summary: Optional[str]) -> int: ...

class NullDbPort(DbPort):
    def ensure_anonymous_user(self) -> str:
        return '00000000-0000-0000-0000-000000000000'
    def begin_session(self, user_id, effective_config):
        return '00000000-0000-0000-0000-000000000001'
    def end_session(self, session_uuid):
        pass
    def create_job(self, user_id, session_uuid, url, requested_types):
        return '00000000-0000-0000-0000-000000000002'
    def update_job(self, *a, **k):
        pass
    def upsert_video(self, user_id, youtube_id, title, raw_info):
        return '00000000-0000-0000-0000-000000000003'
    def record_format_selection(self, *a, **k):
        pass
    def record_media_file(self, *a, **k):
        return 0
    def mark_media_deleted(self, *a, **k):
        pass
    def log_event(self, *a, **k):
        pass
    def record_transcript(self, *a, **k):
        return 0

@dataclass
class _SqlalchemyCtx:
    engine: Any
    SessionLocal: Any

class PostgresDbPort(DbPort):
    def __init__(self, url: str):
        engine = create_engine(url, pool_pre_ping=True, future=True)
        self.ctx = _SqlalchemyCtx(engine=engine, SessionLocal=sessionmaker(bind=engine, expire_on_commit=False, future=True))
        self._anon_user_id = None

    # --- retry wrapper ---
    def _with_retry(self, fn, *args, **kwargs):
        delay = 0.25
        for attempt in range(3):
            try:
                return fn(*args, **kwargs)
            except SQLAlchemyError as e:
                if attempt == 2:
                    raise
                time.sleep(delay)
                delay *= 2

    # --- helpers ---
    def _get_session(self):
        return self.ctx.SessionLocal()

    # --- interface methods ---
    def ensure_anonymous_user(self) -> str:
        if self._anon_user_id:
            return self._anon_user_id
        def _op():
            with self._get_session() as s:
                user = s.query(PlatformUser).filter(PlatformUser.email == ANON_EMAIL).one_or_none()
                if user is None:
                    user = PlatformUser(email=ANON_EMAIL, is_anonymous=True)
                    s.add(user)
                    s.commit()
                    s.refresh(user)
                self._anon_user_id = str(user.id)
                return self._anon_user_id
        return self._with_retry(_op)

    def begin_session(self, user_id: str, effective_config: dict) -> str:
        def _op():
            with self._get_session() as s:
                rec = DbSession(user_id=user_id, effective_config=effective_config)
                s.add(rec)
                s.commit(); s.refresh(rec)
                return str(rec.session_uuid)
        return self._with_retry(_op)

    def end_session(self, session_uuid: str) -> None:
        def _op():
            with self._get_session() as s:
                rec = s.get(DbSession, session_uuid)
                if rec:
                    rec.ended_at = datetime.datetime.now(timezone.utc)
                    s.commit()
        return self._with_retry(_op)

    def create_job(self, user_id: str, session_uuid: Optional[str], url: str, requested_types) -> str:
        def _op():
            with self._get_session() as s:
                job = Job(user_id=user_id, session_uuid=session_uuid, url=url,
                          requested_types=list(requested_types), status='queued', progress=0)
                s.add(job); s.commit(); s.refresh(job)
                return str(job.job_id)
        return self._with_retry(_op)

    def update_job(self, job_id: str, *, status: Optional[str] = None, progress: Optional[int] = None,
                   message: Optional[str] = None, last_error: Optional[str] = None, tries_inc: int = 0) -> None:
        def _op():
            with self._get_session() as s:
                job = s.get(Job, job_id)
                if not job: return
                if status is not None: job.status = status
                if progress is not None: job.progress = int(progress)
                if message is not None: job.message = message
                if last_error is not None: job.last_error = last_error
                if tries_inc: job.tries = int(job.tries or 0) + tries_inc
                s.commit()
        return self._with_retry(_op)

    def upsert_video(self, user_id: str, youtube_id: str, title: Optional[str], raw_info: dict) -> str:
        def _op():
            with self._get_session() as s:
                vid = s.query(Video).filter(Video.user_id==user_id, Video.youtube_id==youtube_id).one_or_none()
                if vid is None:
                    vid = Video(user_id=user_id, youtube_id=youtube_id, title=title, raw_info=raw_info)
                    s.add(vid); s.commit(); s.refresh(vid)
                    return str(vid.video_uuid)
                else:
                    # keep original; only update title/raw_info if provided
                    if title: vid.title = title
                    if raw_info: vid.raw_info = raw_info
                    s.commit(); s.refresh(vid)
                    return str(vid.video_uuid)
        return self._with_retry(_op)

    def record_format_selection(self, user_id: str, video_uuid: str, selection_kind: str,
                                chosen_format_id: Optional[str], scores: dict,
                                preferences_snapshot: dict) -> None:
        def _op():
            with self._get_session() as s:
                rec = FormatSelection(
                    user_id=user_id, video_uuid=video_uuid, selection_kind=selection_kind,
                    chosen_format_id=chosen_format_id,
                    quality_score=scores.get('quality'),
                    format_score=scores.get('format'),
                    size_score=scores.get('size'),
                    total_score=scores.get('total'),
                    attempt_rank=scores.get('attempt_rank'),
                    preferences_snapshot=preferences_snapshot,
                )
                s.add(rec); s.commit()
        return self._with_retry(_op)

    def record_media_file(self, user_id: str, video_uuid: str, kind: str, language_code: Optional[str],
                          path: str, filename: str, ext: str, size_bytes: Optional[int],
                          is_final: bool = True, status: str = 'completed') -> int:
        def _op():
            with self._get_session() as s:
                mf = MediaFile(
                    user_id=user_id, video_uuid=video_uuid, kind=kind, language_code=language_code,
                    path=path, filename=filename, ext=ext, size_bytes=size_bytes,
                    is_final=is_final, status=status,
                )
                s.add(mf); s.commit(); s.refresh(mf)
                return int(mf.id)
        return self._with_retry(_op)

    def mark_media_deleted(self, media_file_id: int, file_moved_to: Optional[str] = None) -> None:
        def _op():
            with self._get_session() as s:
                mf = s.get(MediaFile, media_file_id)
                if mf:
                    mf.status = 'deleted'
                    mf.deleted_at = datetime.datetime.now(timezone.utc)
                    if file_moved_to: mf.file_moved_to = file_moved_to
                    s.commit()
        return self._with_retry(_op)

    def check_existing_media_file(self, user_id: str, video_uuid: str, kind: str, 
                                 language_code: Optional[str], ext: str) -> Optional[Dict]:
        """Check if a media file of the same variant already exists in the database."""
        def _op():
            with self._get_session() as s:
                existing_files = s.query(MediaFile).filter(
                    MediaFile.user_id == user_id,
                    MediaFile.video_uuid == video_uuid,
                    MediaFile.kind == kind,
                    MediaFile.language_code == language_code,
                    MediaFile.ext == ext,
                    MediaFile.is_final == True,
                    MediaFile.status == 'completed'
                ).all()
                
                if existing_files:
                    # Return the most recent one
                    latest_file = max(existing_files, key=lambda x: x.created_at)
                    return {
                        'id': latest_file.id,
                        'path': latest_file.path,
                        'filename': latest_file.filename,
                        'size_bytes': latest_file.size_bytes,
                        'created_at': latest_file.created_at
                    }
                return None
        return self._with_retry(_op)

    def log_event(self, user_id: str, video_uuid: Optional[str], job_id: Optional[str],
                  event_type: str, payload: dict) -> None:
        def _op():
            with self._get_session() as s:
                ev = Event(user_id=user_id, video_uuid=video_uuid, job_id=job_id,
                           event_type=event_type, payload=payload)
                s.add(ev); s.commit()
        return self._with_retry(_op)

    def record_transcript(self, user_id: str, video_uuid: str, media_file_id: Optional[int],
                          path: str, summary: Optional[str]) -> int:
        def _op():
            with self._get_session() as s:
                tr = Transcript(user_id=user_id, video_uuid=video_uuid, media_file_id=media_file_id,
                                path=path, summary=summary)
                s.add(tr); s.commit(); s.refresh(tr)
                return int(tr.id)
        return self._with_retry(_op)

# Factory helper

def get_db_port_from_env() -> DbPort:
    enabled = os.getenv('DATABASE_ENABLED', 'false').lower() in ('1','true','yes','on')
    url = os.getenv('DATABASE_URL')
    if not enabled or not url:
        return NullDbPort()
    try:
        return PostgresDbPort(url)
    except Exception:
        # never break the app
        return NullDbPort() 