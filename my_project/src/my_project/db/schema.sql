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

-- Seed anonymous (donÃ¢â‚¬â„¢t pass id to avoid UUID/bigint mismatch)
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

-- Videos (deÃ¢â‚¬â€˜dup per user by YouTube ID)
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
    path        TEXT NOT NULL,       -- absolute or projectÃ¢â‚¬â€˜relative
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
    chosen_format_id TEXT,              -- ytÃ¢â‚¬â€˜dlp's format id
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
-- Lightweight fullÃ¢â‚¬â€˜text search on summaries
CREATE INDEX IF NOT EXISTS idx_transcripts_summary_fts ON transcripts USING GIN (to_tsvector('simple', COALESCE(summary,'')));

-- Optional housekeeping: autoÃ¢â‚¬â€˜update jobs.updated_at (trigger)
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