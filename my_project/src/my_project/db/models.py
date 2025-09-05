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