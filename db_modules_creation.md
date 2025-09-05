

**Create a .env file in in this directory**
```bash
# .env or system env
DATABASE_ENABLED=true
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/yt_app
```

**Create database**
```bash
psql -U postgres -c "CREATE DATABASE yt_app;"
```

---

## 1) `schema.sql` — exact DDL (PostgreSQL)

**Location**: `my_project/src/my_project/db/schema.sql`

```sql
-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS citext;

-- Enums
DO $$ BEGIN
  CREATE TYPE media_kind AS ENUM ('audio','video','video_with_audio','transcript','metadata');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN
  CREATE TYPE media_status AS ENUM ('completed','deleted','moved');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN
  CREATE TYPE job_status AS ENUM ('queued','running','succeeded','failed','cancelled');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- Users (UUID PK)
CREATE TABLE IF NOT EXISTS platform_users (
  id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  email        CITEXT UNIQUE NOT NULL,
  is_anonymous BOOLEAN NOT NULL DEFAULT FALSE,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Seed anonymous (don’t pass id to avoid UUID/bigint mismatch)
INSERT INTO platform_users (email, is_anonymous)
VALUES ('anonymous@localhost', TRUE)
ON CONFLICT (email) DO NOTHING;

-- Sessions (config snapshot)
CREATE TABLE IF NOT EXISTS sessions (
    session_uuid    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES platform_users(id),
    started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at        TIMESTAMPTZ,
    effective_config JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);

-- Jobs (progress + status)
CREATE TABLE IF NOT EXISTS jobs (
    job_id      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_uuid UUID REFERENCES sessions(session_uuid) ON DELETE SET NULL,
    user_id     UUID NOT NULL REFERENCES platform_users(id),
    url         TEXT NOT NULL,
    requested_types TEXT[] NOT NULL,
    status      job_status NOT NULL DEFAULT 'queued',
    progress    INTEGER NOT NULL DEFAULT 0, -- 0..100
    message     TEXT,
    tries       SMALLINT NOT NULL DEFAULT 0,
    last_error  TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_jobs_user ON jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);

-- Videos (de‑dup per user by YouTube ID)
CREATE TABLE IF NOT EXISTS videos (
    video_uuid  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id     UUID NOT NULL REFERENCES platform_users(id),
    youtube_id  TEXT NOT NULL,
    title       TEXT,
    raw_info    JSONB,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, youtube_id)
);
CREATE INDEX IF NOT EXISTS idx_videos_user ON videos(user_id);

-- Media files (soft delete + exact variant uniqueness)
CREATE TABLE IF NOT EXISTS media_files (
    id          BIGSERIAL PRIMARY KEY,
    user_id     UUID NOT NULL REFERENCES platform_users(id),
    video_uuid  UUID NOT NULL REFERENCES videos(video_uuid),
    kind        media_kind NOT NULL,
    language_code TEXT,              -- e.g., 'en', 'pt-PT'
    path        TEXT NOT NULL,       -- absolute or project‑relative
    filename    TEXT NOT NULL,
    ext         TEXT NOT NULL,       -- 'mp4','mp3','txt','json'
    size_bytes  BIGINT,
    is_final    BOOLEAN NOT NULL DEFAULT TRUE,
    status      media_status NOT NULL DEFAULT 'completed',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at  TIMESTAMPTZ,
    file_moved_to TEXT
);
CREATE INDEX IF NOT EXISTS idx_media_user ON media_files(user_id);
CREATE INDEX IF NOT EXISTS idx_media_video ON media_files(video_uuid);
CREATE INDEX IF NOT EXISTS idx_media_status ON media_files(status);
-- Enforce exact variant uniqueness (normalize NULLs)
CREATE UNIQUE INDEX IF NOT EXISTS uniq_media_variant ON media_files (
    video_uuid, kind, COALESCE(language_code, ''), ext, is_final
);

-- Why a format was chosen (debug + reproducibility)
CREATE TABLE IF NOT EXISTS format_selection (
    id              BIGSERIAL PRIMARY KEY,
    user_id         UUID NOT NULL REFERENCES platform_users(id),
    video_uuid      UUID NOT NULL REFERENCES videos(video_uuid),
    selection_kind  TEXT NOT NULL,      -- 'audio','video','merged', etc.
    chosen_format_id TEXT,              -- yt‑dlp's format id
    quality_score   NUMERIC(6,3),
    format_score    NUMERIC(6,3),
    size_score      NUMERIC(6,3),
    total_score     NUMERIC(6,3),
    attempt_rank    INTEGER,            -- 1 = first choice
    preferences_snapshot JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_fmt_user_video ON format_selection(user_id, video_uuid);

-- Event trail (verbose)
CREATE TABLE IF NOT EXISTS events (
    id          BIGSERIAL PRIMARY KEY,
    user_id     UUID NOT NULL REFERENCES platform_users(id),
    video_uuid  UUID REFERENCES videos(video_uuid),
    job_id      UUID REFERENCES jobs(job_id),
    event_type  TEXT NOT NULL,         -- e.g., 'INFO_FETCHED','FORMAT_SELECTED','AUDIO_LANG_FALLBACK','DOWNLOAD_COMPLETED','RETRY','ERROR'
    payload     JSONB,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_events_user_time ON events(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_events_job ON events(job_id);

-- Transcripts (keep forever; text not stored, only path + summary)
CREATE TABLE IF NOT EXISTS transcripts (
    id              BIGSERIAL PRIMARY KEY,
    user_id         UUID NOT NULL REFERENCES platform_users(id),
    video_uuid      UUID NOT NULL REFERENCES videos(video_uuid),
    media_file_id   BIGINT REFERENCES media_files(id) ON DELETE SET NULL,
    path            TEXT NOT NULL,   -- where the .txt/.vtt lives
    summary         TEXT,            -- short text for search; full text remains on disk
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_transcripts_user ON transcripts(user_id);
CREATE INDEX IF NOT EXISTS idx_transcripts_video ON transcripts(video_uuid);
-- Lightweight full‑text search on summaries
CREATE INDEX IF NOT EXISTS idx_transcripts_summary_fts ON transcripts USING GIN (to_tsvector('simple', COALESCE(summary,'')));

-- Optional housekeeping: auto‑update jobs.updated_at (trigger)
CREATE OR REPLACE FUNCTION set_updated_at() RETURNS TRIGGER AS $func$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END
$func$ LANGUAGE plpgsql;

-- Create trigger (idempotent)
DO $$ BEGIN
  CREATE TRIGGER trg_jobs_updated_at
  BEFORE UPDATE ON jobs
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
```

**run psql command** 
```bash
psql -U postgres -d yt_app -f my_project/src/my_project/db/schema.sql
```

---

## 2) `models.py` — SQLAlchemy (2.x) models

**Location**: `my_project/src/my_project/db/models.py`

```python
#  models.py
from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Column, String, Boolean, DateTime, Integer, BigInteger, Text, ForeignKey,
    UniqueConstraint, Index, JSON, create_engine, Enum as SAEnum, ARRAY, Numeric, text
)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

Base = declarative_base()

def utc_now():
    """Helper function to get current UTC datetime for SQLAlchemy defaults"""
    return datetime.now(timezone.utc)

MediaKind = SAEnum(
    'audio','video','video_with_audio','transcript','metadata',
    name='media_kind', native_enum=True, create_type=False
)
MediaStatus = SAEnum(
    'completed','deleted','moved',
    name='media_status', native_enum=True, create_type=False
)
JobStatus = SAEnum(
    'queued','running','succeeded','failed','cancelled',
    name='job_status', native_enum=True, create_type=False
)

class PlatformUser(Base):
    __tablename__ = 'platform_users'
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text('uuid_generate_v4()'))
    email = Column(String, nullable=False, unique=True)
    is_anonymous = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=utc_now)

class Session(Base):
    __tablename__ = 'sessions'
    session_uuid = Column(UUID(as_uuid=True), primary_key=True, server_default=text('uuid_generate_v4()'))
    user_id = Column(UUID(as_uuid=True), ForeignKey('platform_users.id'), nullable=False)
    started_at = Column(DateTime, nullable=False, default=utc_now)
    ended_at = Column(DateTime)
    effective_config = Column(JSONB, nullable=False, default=dict)

class Job(Base):
    __tablename__ = 'jobs'
    job_id = Column(UUID(as_uuid=True), primary_key=True, server_default=text('uuid_generate_v4()'))
    session_uuid = Column(UUID(as_uuid=True), ForeignKey('sessions.session_uuid'))
    user_id = Column(UUID(as_uuid=True), ForeignKey('platform_users.id'), nullable=False)
    url = Column(Text, nullable=False)
    requested_types = Column(ARRAY(String), nullable=False)
    status = Column(JobStatus, nullable=False, default='queued')
    progress = Column(Integer, nullable=False, default=0)
    message = Column(Text)
    tries = Column(Integer, nullable=False, default=0)
    last_error = Column(Text)
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now)

class Video(Base):
    __tablename__ = 'videos'
    video_uuid = Column(UUID(as_uuid=True), primary_key=True, server_default=text('uuid_generate_v4()'))
    user_id = Column(UUID(as_uuid=True), ForeignKey('platform_users.id'), nullable=False)
    youtube_id = Column(Text, nullable=False)
    title = Column(Text)
    raw_info = Column(JSONB)
    created_at = Column(DateTime, nullable=False, default=utc_now)
    __table_args__ = (
        UniqueConstraint('user_id', 'youtube_id', name='uq_video_user_youtube'),
    )

class MediaFile(Base):
    __tablename__ = 'media_files'
    id = Column(BigInteger, primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('platform_users.id'), nullable=False)
    video_uuid = Column(UUID(as_uuid=True), ForeignKey('videos.video_uuid'), nullable=False)
    kind = Column(MediaKind, nullable=False)
    language_code = Column(String)
    path = Column(Text, nullable=False)
    filename = Column(Text, nullable=False)
    ext = Column(String, nullable=False)
    size_bytes = Column(BigInteger)
    is_final = Column(Boolean, nullable=False, default=True)
    status = Column(MediaStatus, nullable=False, default='completed')
    created_at = Column(DateTime, nullable=False, default=utc_now)
    deleted_at = Column(DateTime)
    file_moved_to = Column(Text)


class FormatSelection(Base):
    __tablename__ = 'format_selection'
    id = Column(BigInteger, primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('platform_users.id'), nullable=False)
    video_uuid = Column(UUID(as_uuid=True), ForeignKey('videos.video_uuid'), nullable=False)
    selection_kind = Column(String, nullable=False)
    chosen_format_id = Column(String)
    quality_score = Column(Numeric)  
    format_score = Column(Numeric)
    size_score = Column(Numeric)
    total_score = Column(Numeric)
    attempt_rank = Column(Integer)
    preferences_snapshot = Column(JSONB)
    created_at = Column(DateTime, nullable=False, default=utc_now)

class Event(Base):
    __tablename__ = 'events'
    id = Column(BigInteger, primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('platform_users.id'), nullable=False)
    video_uuid = Column(UUID(as_uuid=True), ForeignKey('videos.video_uuid'))
    job_id = Column(UUID(as_uuid=True), ForeignKey('jobs.job_id'))
    event_type = Column(String, nullable=False)
    payload = Column(JSONB)
    created_at = Column(DateTime, nullable=False, default=utc_now)

class Transcript(Base):
    __tablename__ = 'transcripts'
    id = Column(BigInteger, primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('platform_users.id'), nullable=False)
    video_uuid = Column(UUID(as_uuid=True), ForeignKey('videos.video_uuid'), nullable=False)
    media_file_id = Column(BigInteger, ForeignKey('media_files.id'))
    path = Column(Text, nullable=False)
    summary = Column(Text)
    created_at = Column(DateTime, nullable=False, default=utc_now)
```

---

## 3) `db_port.py` — tiny adapter with retries (Null + Postgres)

**Location**: `my_project/src/my_project/db/db_port.py`

```python
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
    """Interface for DB sideâ€‘effects. Keep calls minimal and idempotent where possible."""
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
```

---

## 4) `download_manager.py` — Wiring points 

**New File**: `my_project/src/my_project/download_manager.py`

```python
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
    create_download_structure, load_normalized_config,
    generate_video_uuid
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
            
            # Step 3: Generate video UUID and setup directories
            video_uuid = generate_video_uuid()
            logger.debug(f"Generated video UUID: {video_uuid}")
            
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
                    args, uid, vid, jid
                )
                if success:
                    success_count += 1
                    logger.info("✅ Audio download completed successfully")
                else:
                    logger.warning("❌ Audio download failed")
            except Exception as e:
                logger.error(f"💥 Audio download error: {str(e)}")
        
        # Process video-only download
        if args.get('video_only'):
            logger.debug("Processing video-only download with database logging")
            try:
                success = self._download_video_with_db(
                    url, formats, video_uuid, session_uuid, base_downloads_dir,
                    args, uid, vid, jid
                )
                if success:
                    success_count += 1
                    logger.info("✅ Video download completed successfully")
                else:
                    logger.warning("❌ Video download failed")
            except Exception as e:
                logger.error(f"💥 Video download error: {str(e)}")
        
        # Process video+audio download  
        if args.get('video_with_audio'):
            logger.debug("Processing video+audio download with database logging")
            try:
                success = self._download_video_audio_with_db(
                    url, formats, video_uuid, session_uuid, base_downloads_dir,
                    args, uid, vid, jid
                )
                if success:
                    success_count += 1
                    logger.info("✅ Video+audio download completed successfully") 
                else:
                    logger.warning("❌ Video+audio download failed")
            except Exception as e:
                logger.error(f"💥 Video+audio download error: {str(e)}")
        
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
                    logger.info("✅ Transcript download completed successfully")
                else:
                    logger.warning("❌ Transcript download failed")
            except Exception as e:
                logger.error(f"💥 Transcript download error: {str(e)}")
        
        results["success_count"] = success_count
        logger.info(f"📊 Downloads completed: {success_count}/{total_requested}")
        return results
    
    def _download_audio_with_db(self, url: str, formats: List, video_uuid: str, 
                               session_uuid: str, base_downloads_dir: str, 
                               args: Dict, uid, vid, jid) -> bool:
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
        
        # Setup download path
        audio_dir = create_download_structure(base_downloads_dir, session_uuid, video_uuid, "audio")
        template = get_filename_template()
        filename = str(audio_dir / template)
        
        logger.debug(f"Audio download path: {filename}")
        
        # Perform download
        try:
            from .core_CLI import download_audio_with_fallback
            success = download_audio_with_fallback(url, audio_list, filename)
            
            if success:
                # Record successful download in database
                file_path = Path(filename)
                if file_path.exists():
                    file_size = file_path.stat().st_size
                    file_name = file_path.name
                    
                    mid = self.safe_db_operation("record_media_file", self.db.record_media_file,
                                               uid, vid, 'audio', None, str(file_path), file_name, 
                                               default_audio.get('ext', 'unknown'), file_size)
                    
                    self.safe_db_operation("log_event", self.db.log_event,
                                         uid, vid, jid, 'DOWNLOAD_COMPLETED', 
                                         {'path': str(file_path), 'type': 'audio', 'format_id': default_audio.get('format_id')})
                    logger.debug(f"Audio download logged in database: {file_path}")
            
            return success
            
        except Exception as e:
            error_msg = f"Audio download failed: {str(e)}"
            self.safe_db_operation("log_event", self.db.log_event,
                                 uid, vid, jid, 'ERROR', {'error': error_msg, 'type': 'audio'})
            logger.error(error_msg)
            return False
    
    def _download_video_with_db(self, url: str, formats: List, video_uuid: str,
                               session_uuid: str, base_downloads_dir: str,
                               args: Dict, uid, vid, jid) -> bool:
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
        
        # Setup download path
        video_dir = create_download_structure(base_downloads_dir, session_uuid, video_uuid, "video")
        template = get_filename_template()
        filename = str(video_dir / template)
        
        logger.debug(f"Video download path: {filename}")
        
        # Perform download
        try:
            from .core_CLI import download_video_with_fallback
            success = download_video_with_fallback(url, video_list, filename)
            
            if success:
                # Record successful download in database
                file_path = Path(filename)
                if file_path.exists():
                    file_size = file_path.stat().st_size
                    file_name = file_path.name
                    
                    mid = self.safe_db_operation("record_media_file", self.db.record_media_file,
                                               uid, vid, 'video', None, str(file_path), file_name,
                                               default_video.get('ext', 'unknown'), file_size)
                    
                    self.safe_db_operation("log_event", self.db.log_event,
                                         uid, vid, jid, 'DOWNLOAD_COMPLETED',
                                         {'path': str(file_path), 'type': 'video', 'format_id': default_video.get('format_id')})
                    logger.debug(f"Video download logged in database: {file_path}")
            
            return success
            
        except Exception as e:
            error_msg = f"Video download failed: {str(e)}"
            self.safe_db_operation("log_event", self.db.log_event,
                                 uid, vid, jid, 'ERROR', {'error': error_msg, 'type': 'video'})
            logger.error(error_msg)
            return False
    
    def _download_video_audio_with_db(self, url: str, formats: List, video_uuid: str,
                                     session_uuid: str, base_downloads_dir: str,
                                     args: Dict, uid, vid, jid) -> bool:
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
        filename = str(video_audio_dir / template)
        
        logger.debug(f"Video+audio download path: {filename}")
        
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
            logger.debug(f"🎵 Preferred audio languages: {', '.join(preferred_langs)}")
            
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
                
                logger.debug(f"📹 Using combined format: {selected_format} (language: {_fmt_audio_lang(selected_combined) or 'unknown'})")
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
                    
                    logger.debug(f"📹 Using separate streams: {selected_format} (audio language: {_fmt_audio_lang(audio_fmt) or 'unknown'})")
                elif require_lang:
                    error_msg = f"Requested audio language(s) {preferred_langs} not available for this video"
                    self.safe_db_operation("log_event", self.db.log_event,
                                         uid, vid, jid, 'ERROR', {'error': error_msg, 'type': 'video_with_audio'})
                    logger.error(error_msg)
                    return False
        
        # Fallback to best available if no language match or no preference
        if not selected_format:
            logger.debug("⚠️ No language match found, falling back to best quality")
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
        
        # Perform download
        try:
            success = download_video_with_audio(url, args.get('quality') or "720p", filename, format_override=selected_format)
            
            if success:
                # Record successful download in database
                file_path = Path(filename)
                if file_path.exists():
                    file_size = file_path.stat().st_size
                    file_name = file_path.name
                    
                    # Determine audio language for database record
                    audio_lang = None
                    if format_method in ["combined_with_lang", "separate_with_lang"] and preferred_langs:
                        audio_lang = preferred_langs[0]  # Use first preferred language as recorded language
                    
                    mid = self.safe_db_operation("record_media_file", self.db.record_media_file,
                                               uid, vid, 'video_with_audio', audio_lang, str(file_path), file_name,
                                               'mp4', file_size)  # Most video+audio downloads result in mp4
                    
                    self.safe_db_operation("log_event", self.db.log_event,
                                         uid, vid, jid, 'DOWNLOAD_COMPLETED',
                                         {'path': str(file_path), 'type': 'video_with_audio', 'format_method': format_method, 'format_id': selected_format})
                    logger.debug(f"Video+audio download logged in database: {file_path}")
            
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
```

---

## 5) `core_CLI.py` Core CLI Integration

**Location**: `my_project/src/my_project/core_CLI.py`

```python
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
        
        # 🆕 Use database-aware download manager for logging
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
        logger.info(f"🔄 Starting database-aware download for {url}")
        return download_manager.run_download_with_db(url, session_uuid, base_downloads_dir, args_dict)
        
    except Exception as e:
        print(f"💥 Error processing video {url}: {str(e)}")
        logger.error(f"Error processing video {url}: {str(e)}")
        return {"status": "error", "url": url, "error": str(e)}


def process_info_only_mode(url: str, session_uuid: str, base_downloads_dir: str, args) -> dict:
    """Handle info-only mode (original logic without database logging)."""
    try:
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
        print(f"💥 Error processing video {url}: {str(e)}")
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
            print(f"\n🔧 CLI Override: --quality {args.quality}")
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
            print(f"\n🔧 CLI Override: --transcript-formats {args.transcript_formats}")
            if "transcripts" not in effective_config:
                effective_config["transcripts"] = {}
            if "processing" not in effective_config["transcripts"]:
                effective_config["transcripts"]["processing"] = {}
            effective_config["transcripts"]["processing"]["output_formats_list"] = args.transcript_formats
        
        # Show audio language overrides
        if hasattr(args, 'audio_lang') and args.audio_lang:
            print(f"\n🔧 CLI Override: --audio-lang {args.audio_lang}")
            if "quality_preferences" not in effective_config:
                effective_config["quality_preferences"] = {}
            if "audio" not in effective_config["quality_preferences"]:
                effective_config["quality_preferences"]["audio"] = {}
            effective_config["quality_preferences"]["audio"]["preferred_languages"] = args.audio_lang
        
        if hasattr(args, 'require_audio_lang') and args.require_audio_lang:
            print(f"\n🔧 CLI Override: --require-audio-lang")
            if "quality_preferences" not in effective_config:
                effective_config["quality_preferences"] = {}
            if "audio" not in effective_config["quality_preferences"]:
                effective_config["quality_preferences"]["audio"] = {}
            effective_config["quality_preferences"]["audio"]["require_language_match"] = True
        
        # Show output directory override
        if hasattr(args, 'outdir') and args.outdir and args.outdir != ".":
            print(f"\n🔧 CLI Override: --outdir {args.outdir}")
            effective_config["downloads"]["base_directory"] = args.outdir
        
        # Pretty print the effective configuration
        import json
        print("\n📋 Configuration JSON:")
        print(json.dumps(effective_config, indent=2, ensure_ascii=False))
        
        # Show key selections that will be used
        print("\n" + "=" * 60)
        print("KEY EFFECTIVE SETTINGS")
        print("=" * 60)
        
        video_prefs = effective_config.get("quality_preferences", {}).get("video", {})
        audio_prefs = effective_config.get("quality_preferences", {}).get("audio", {})
        transcript_prefs = effective_config.get("transcripts", {}).get("processing", {})
        
        print(f"📹 Video Quality: {video_prefs.get('preferred_quality', 'DEFAULT')}")
        print(f"🎵 Audio Quality: {audio_prefs.get('preferred_quality', 'DEFAULT')}")
        print(f"🎵 Audio Languages: {audio_prefs.get('preferred_languages', ['DEFAULT'])}")
        print(f"🔒 Require Audio Language: {audio_prefs.get('require_language_match', 'DEFAULT')}")
        print(f"📝 Transcript Formats: {transcript_prefs.get('output_formats_list', ['DEFAULT'])}")
        print(f"📁 Output Directory: {effective_config.get('downloads', {}).get('base_directory', 'DEFAULT')}")
        print(f"🔧 Sanitize Filenames: {effective_config.get('behavior', {}).get('sanitize_filenames', 'DEFAULT')}")
        print(f"📏 Max Filename Length: {effective_config.get('behavior', {}).get('max_filename_length', 'DEFAULT')}")
        
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Error loading configuration: {e}")


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
```

## 6) `__main__.py` — load .env  

**Location**: `my_project/src/my_project/__main__.py`

```python
# __main_.py
def main():
    from .core_CLI import main as cli_main
    from dotenv import load_dotenv
    from pathlib import Path
    
    # Look for .env file in parent directories
    env_path = Path(__file__).parent.parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
    else:
        # Fallback to default behavior
        load_dotenv()
    
    cli_main()

if __name__ == "__main__":
    main()
```

## Key Files

1. **my_project/src/my_project/__main__.py** - Environment loading fix
2. **my_project/src/my_project/db/models.py** - Schema fixes and UUID defaults
3. **my_project/src/my_project/core_CLI.py** - Database integration
4. **my_project/src/my_project/download_manager.py** - New file for database-aware downloads


