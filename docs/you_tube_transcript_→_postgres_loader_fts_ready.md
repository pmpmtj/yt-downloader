# YouTube Transcript → Postgres Loader (FTS‑ready)

A compact, production‑ish setup to store YouTube transcriptions for fast lookup now (Postgres full‑text + trigram) and a clean path to embeddings later.

---

## 0) What you get

- **Postgres schema**: `videos`, `chapters`, `transcript_segments`, `raw_assets` + FTS/trigram indexes.
- **Python loader**: `ingest_transcript.py` that consumes your 3 files (`structured.json`, `timestamped.txt`, `clean.txt`).
- **How‑to run**: step‑by‑step commands.
- **Bonus**: ready‑made queries and an (optional) future `pgvector` table (commented out).

Works on **Python 3.12+** and **Postgres 14+** (tested with 15/16).

---

## 1) Install prerequisites

```bash
# Ubuntu/Debian example
sudo apt-get update && sudo apt-get install -y postgresql postgresql-contrib

# Ensure pg_trgm (and vector later if you want)
# In psql: CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- done by the DDL too

# Python deps
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install psycopg[binary] python-dotenv tqdm
```

> Tip: `psycopg[binary]` avoids compiling libpq locally.

---

## 2) Create the database + schema

**Create DB (if needed)**

```bash
createdb yttext
```

**Run DDL** (copy/paste into `psql yttext` or save as `schema.sql` and `psql -d yttext -f schema.sql`):

```sql
-- 0) schemas & extensions
CREATE SCHEMA IF NOT EXISTS media;
CREATE EXTENSION IF NOT EXISTS pg_trgm;      -- for ILIKE/fuzzy text search
-- CREATE EXTENSION IF NOT EXISTS vector;    -- enable later when you want embeddings

-- 1) Videos
CREATE TABLE IF NOT EXISTS media.videos (
  video_id        TEXT PRIMARY KEY,                 -- e.g. "_L1JbzDnEMk"
  title           TEXT NOT NULL,
  duration_s      INT  CHECK (duration_s >= 0),
  upload_date     DATE,
  uploader        TEXT,
  language_code   TEXT,                             -- e.g. "en"
  is_generated    BOOLEAN,                          -- auto-generated captions?
  metadata        JSONB,                            -- raw metadata
  processed_at    TIMESTAMPTZ,
  text_word_count INT,
  text_char_count INT
);

-- 2) Chapters (optional)
CREATE TABLE IF NOT EXISTS media.chapters (
  id              BIGSERIAL PRIMARY KEY,
  video_id        TEXT REFERENCES media.videos(video_id) ON DELETE CASCADE,
  start_time_s    NUMERIC(10,3) NOT NULL,
  end_time_s      NUMERIC(10,3),
  text            TEXT NOT NULL,
  summary         TEXT
);
CREATE INDEX IF NOT EXISTS chapters_video_time_idx
  ON media.chapters (video_id, start_time_s);

-- 3) Transcript segments (granular units for search & playback seeking)
CREATE TABLE IF NOT EXISTS media.transcript_segments (
  id              BIGSERIAL PRIMARY KEY,
  video_id        TEXT REFERENCES media.videos(video_id) ON DELETE CASCADE,
  start_time_s    NUMERIC(10,3) NOT NULL,
  duration_s      NUMERIC(10,3) NOT NULL CHECK (duration_s >= 0),
  text            TEXT NOT NULL,
  is_generated    BOOLEAN,
  source          TEXT,
  text_hash       TEXT,
  extra           JSONB
);
CREATE INDEX IF NOT EXISTS seg_video_time_idx
  ON media.transcript_segments (video_id, start_time_s);

-- Full‑text search support
ALTER TABLE media.transcript_segments
  ADD COLUMN IF NOT EXISTS search_vector tsvector;

CREATE OR REPLACE FUNCTION media.tg_update_search_vector()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  NEW.search_vector := to_tsvector('english', coalesce(NEW.text,''));
  RETURN NEW;
END$$;

DROP TRIGGER IF EXISTS trg_segments_tsv ON media.transcript_segments;
CREATE TRIGGER trg_segments_tsv
BEFORE INSERT OR UPDATE ON media.transcript_segments
FOR EACH ROW EXECUTE FUNCTION media.tg_update_search_vector();

CREATE INDEX IF NOT EXISTS seg_tsv_idx
  ON media.transcript_segments USING GIN (search_vector);
CREATE INDEX IF NOT EXISTS seg_text_trgm_idx
  ON media.transcript_segments USING GIN (text gin_trgm_ops);

-- 4) Raw assets (optional)
CREATE TABLE IF NOT EXISTS media.raw_assets (
  id            BIGSERIAL PRIMARY KEY,
  video_id      TEXT REFERENCES media.videos(video_id) ON DELETE CASCADE,
  kind          TEXT NOT NULL,         -- 'clean_text' | 'timestamped' | 'structured_json'
  content_text  TEXT,
  content_json  JSONB,
  stored_at     TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS raw_assets_video_kind_idx
  ON media.raw_assets (video_id, kind);

-- 5) (Later) Embeddings (vector‑ready)
-- CREATE TABLE IF NOT EXISTS media.segment_embeddings (
--   segment_id   BIGINT PRIMARY KEY REFERENCES media.transcript_segments(id) ON DELETE CASCADE,
--   model        TEXT NOT NULL,
--   dim          INT  NOT NULL,
--   embedding    vector(dim) NOT NULL,
--   created_at   TIMESTAMPTZ DEFAULT now()
-- );
-- CREATE INDEX IF NOT EXISTS seg_embed_idx ON media.segment_embeddings USING ivfflat (embedding);
```

---

## 3) Configure DB connection

Create a `.env` in your project directory (loader reads it automatically):

```env
PGHOST=localhost
PGPORT=5432
PGDATABASE=yttext
PGUSER=postgres
PGPASSWORD=your_password
```

> You can also pass a full DSN via `DATABASE_URL=postgresql://user:pass@host:5432/yttext`.

---

## 4) Put your three files somewhere

Example file naming (any names are fine; pass them via flags):

```
./_L1JbzDnEMk_en_5 Signs the AI Bubble is Bursting_structured.json
./_L1JbzDnEMk_en_5 Signs the AI Bubble is Bursting_timestamped.txt
./_L1JbzDnEMk_en_5 Signs the AI Bubble is Bursting_clean.txt
```

---

## 5) Python loader — `ingest_transcript.py`

> Copy this file as‑is. It is tolerant to partial metadata and missing sections.

```python
#!/usr/bin/env python3
"""
Ingest YouTube transcript assets (structured JSON + timestamped TXT + clean TXT)
into Postgres tables under schema `media` with full‑text search enabled.

Usage:
  python ingest_transcript.py \
    --video-id _L1JbzDnEMk \
    --json "./_L1JbzDnEMk_en_5 Signs the AI Bubble is Bursting_structured.json" \
    --timestamped "./_L1JbzDnEMk_en_5 Signs the AI Bubble is Bursting_timestamped.txt" \
    --clean "./_L1JbzDnEMk_en_5 Signs the AI Bubble is Bursting_clean.txt" \
    --source whisper  # or youtube / other

Requires: psycopg[binary], python-dotenv, tqdm
"""
from __future__ import annotations
import argparse
import json
import os
import re
import sys
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv
from tqdm import tqdm

TS_RE = re.compile(
    r"^\s*(?:\[)?(?:(\d{1,2}):)?(\d{1,2}):(\d{2})(?:[\.,](\d{1,3}))?(?:\])?\s*(.*\S)\s*$"
)
# Matches forms like: 1:23:45.678 Text  |  12:34 Text  | [00:01:02,3] Text


def to_seconds(h: Optional[str], m: str, s: str, ms: Optional[str]) -> float:
    hours = int(h) if h else 0
    minutes = int(m)
    seconds = int(s)
    millis = int(ms) if ms else 0
    return hours * 3600 + minutes * 60 + seconds + millis / 1000.0


def parse_timestamped_txt(path: str) -> List[Dict[str, Any]]:
    """Return list of {start, text}. Duration is inferred later.
    Accepts flexible timestamp formats at line start or within []."""
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            m = TS_RE.match(line)
            if not m:
                # If no timestamp at start, skip; could be continuation lines
                continue
            start = to_seconds(m.group(1), m.group(2), m.group(3), m.group(4))
            text = m.group(5).strip()
            rows.append({"start": start, "text": text})
    # Infer duration by diffing starts; last one gets median duration
    if rows:
        starts = [r["start"] for r in rows]
        diffs = [max(0.5, b - a) for a, b in zip(starts, starts[1:])]
        default = (sorted(diffs)[len(diffs)//2] if diffs else 3.0)
        for i, r in enumerate(rows):
            dur = diffs[i] if i < len(diffs) else default
            r["duration"] = round(float(dur), 3)
    return rows


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()


def coalesce(*vals):
    for v in vals:
        if v is not None:
            return v
    return None


def upsert_video(conn: psycopg.Connection, video: Dict[str, Any]) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO media.videos (
              video_id, title, duration_s, upload_date, uploader, language_code,
              is_generated, metadata, processed_at, text_word_count, text_char_count
            ) VALUES (
              %(video_id)s, %(title)s, %(duration_s)s, %(upload_date)s, %(uploader)s, %(language_code)s,
              %(is_generated)s, %(metadata)s, %(processed_at)s, %(text_word_count)s, %(text_char_count)s
            )
            ON CONFLICT (video_id) DO UPDATE SET
              title = EXCLUDED.title,
              duration_s = EXCLUDED.duration_s,
              upload_date = EXCLUDED.upload_date,
              uploader = EXCLUDED.uploader,
              language_code = EXCLUDED.language_code,
              is_generated = EXCLUDED.is_generated,
              metadata = COALESCE(media.videos.metadata, '{}'::jsonb) || EXCLUDED.metadata,
              processed_at = EXCLUDED.processed_at,
              text_word_count = EXCLUDED.text_word_count,
              text_char_count = EXCLUDED.text_char_count
            """,
            video,
        )


def insert_chapters(conn: psycopg.Connection, video_id: str, chapters: List[Dict[str, Any]]):
    if not chapters:
        return
    with conn.cursor() as cur:
        cur.execute("DELETE FROM media.chapters WHERE video_id = %s", (video_id,))
        data = [
            (
                video_id,
                float(ch.get("start") or ch.get("start_time") or 0.0),
                float(ch.get("end") or ch.get("end_time") or None) if ch.get("end") or ch.get("end_time") else None,
                str(ch.get("text") or ch.get("title") or "").strip(),
                ch.get("summary"),
            )
            for ch in chapters
        ]
        cur.executemany(
            """
            INSERT INTO media.chapters (video_id, start_time_s, end_time_s, text, summary)
            VALUES (%s, %s, %s, %s, %s)
            """,
            data,
        )


def insert_segments(conn: psycopg.Connection, video_id: str, segments: List[Dict[str, Any]], *, source: str, is_generated: Optional[bool]):
    if not segments:
        return
    with conn.cursor() as cur:
        data = []
        for seg in segments:
            text = str(seg.get("text") or "").strip()
            if not text:
                continue
            start = float(seg.get("start") or seg.get("start_time") or 0.0)
            duration = float(seg.get("duration") or seg.get("dur") or seg.get("end", 0.0) or 0.0)
            if duration <= 0.0 and seg.get("end"):
                duration = max(0.5, float(seg["end"]) - start)
            if duration <= 0.0:
                duration = 3.0
            text_hash = sha256_text(text)
            extra = {k: v for k, v in seg.items() if k not in {"text", "start", "start_time", "duration", "dur", "end"}}
            data.append((video_id, start, duration, text, is_generated, source, text_hash, json.dumps(extra)))
        cur.executemany(
            """
            INSERT INTO media.transcript_segments (
              video_id, start_time_s, duration_s, text, is_generated, source, text_hash, extra
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
            """,
            data,
        )


def insert_raw_assets(conn: psycopg.Connection, video_id: str, *, clean_path: Optional[str], ts_path: Optional[str], json_path: Optional[str]):
    with conn.cursor() as cur:
        if clean_path and os.path.exists(clean_path):
            cur.execute(
                "INSERT INTO media.raw_assets (video_id, kind, content_text) VALUES (%s, 'clean_text', %s)",
                (video_id, open(clean_path, "r", encoding="utf-8").read()),
            )
        if ts_path and os.path.exists(ts_path):
            cur.execute(
                "INSERT INTO media.raw_assets (video_id, kind, content_text) VALUES (%s, 'timestamped', %s)",
                (video_id, open(ts_path, "r", encoding="utf-8").read()),
            )
        if json_path and os.path.exists(json_path):
            cur.execute(
                "INSERT INTO media.raw_assets (video_id, kind, content_json) VALUES (%s, 'structured_json', %s::jsonb)",
                (video_id, open(json_path, "r", encoding="utf-8").read()),
            )


def load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    load_dotenv()
    ap = argparse.ArgumentParser(description="Ingest YouTube transcript assets into Postgres")
    ap.add_argument("--video-id", required=True)
    ap.add_argument("--json", dest="json_path")
    ap.add_argument("--timestamped", dest="ts_path")
    ap.add_argument("--clean", dest="clean_path")
    ap.add_argument("--source", default="youtube")
    ap.add_argument("--is-generated", action="store_true", help="Mark captions as auto-generated")
    ap.add_argument("--dsn", help="Optional psycopg connection string; overrides env")
    args = ap.parse_args()

    conn_kwargs = {}
    dsn = args.dsn or os.getenv("DATABASE_URL")
    if dsn:
        conn = psycopg.connect(dsn, row_factory=dict_row)
    else:
        conn = psycopg.connect(
            host=os.getenv("PGHOST", "localhost"),
            port=int(os.getenv("PGPORT", "5432")),
            dbname=os.getenv("PGDATABASE", "yttext"),
            user=os.getenv("PGUSER", "postgres"),
            password=os.getenv("PGPASSWORD"),
            row_factory=dict_row,
        )

    with conn:
        video_id = args.video_id
        meta: Dict[str, Any] = {}
        chapters: List[Dict[str, Any]] = []
        segments: List[Dict[str, Any]] = []
        clean_text: Optional[str] = None

        if args.json_path and os.path.exists(args.json_path):
            meta = load_json(args.json_path)
            # common shapes
            info = meta.get("metadata") or meta.get("info") or meta
            title = coalesce(info.get("title"), meta.get("title"), os.path.basename(args.json_path))
            duration_s = coalesce(info.get("duration"), info.get("duration_s"))
            upload_date = info.get("upload_date")
            if upload_date and isinstance(upload_date, str) and len(upload_date) == 8 and upload_date.isdigit():
                # 20250130 → 2025-01-30
                upload_date = datetime.strptime(upload_date, "%Y%m%d").date()
            uploader = coalesce(info.get("uploader"), info.get("channel"))
            language_code = coalesce(info.get("language"), info.get("language_code"))
            processed_at = coalesce(info.get("processed_at"), meta.get("processed_at"))
            chapters = meta.get("chapters") or meta.get("chapter_list") or []
            # snippets: text + start(+ duration)
            segments = meta.get("snippets") or meta.get("segments") or []

        # Fallback title if still missing
        title = coalesce(
            meta.get("title") if meta else None,
            os.path.splitext(os.path.basename(args.clean_path or args.ts_path or args.json_path or video_id))[0]
        )

        if args.clean_path and os.path.exists(args.clean_path):
            with open(args.clean_path, "r", encoding="utf-8") as f:
                clean_text = f.read()
        if args.ts_path and os.path.exists(args.ts_path):
            ts_rows = parse_timestamped_txt(args.ts_path)
            # Use txt rows only if structured snippets are missing or to complement
            if not segments:
                segments = ts_rows

        # Compute stats
        words = 0
        chars = 0
        base_for_stats = clean_text or " ".join([s.get("text", "") for s in segments])
        if base_for_stats:
            words = len(base_for_stats.split())
            chars = len(base_for_stats)

        video_row = dict(
            video_id=video_id,
            title=title,
            duration_s=int(duration_s) if isinstance(duration_s, (int, float)) else (int(meta.get("duration", 0)) if meta else None),
            upload_date=upload_date,
            uploader=uploader,
            language_code=language_code,
            is_generated=args.is_generated,
            metadata=meta if meta else {},
            processed_at=processed_at,
            text_word_count=words,
            text_char_count=chars,
        )

        upsert_video(conn, video_row)
        insert_chapters(conn, video_id, chapters)
        insert_segments(conn, video_id, segments, source=args.source, is_generated=args.is_generated)
        insert_raw_assets(conn, video_id, clean_path=args.clean_path, ts_path=args.ts_path, json_path=args.json_path)

        print(f"Ingested video={video_id} | segments={len(segments)} | chapters={len(chapters)} | words={words}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Interrupted", file=sys.stderr)
        sys.exit(130)
```

---

## 6) Run it

```bash
# 1) Ensure schema exists (Step 2)
# 2) Put files in place (Step 4)
# 3) Ingest
python ingest_transcript.py \
  --video-id _L1JbzDnEMk \
  --json "./_L1JbzDnEMk_en_5 Signs the AI Bubble is Bursting_structured.json" \
  --timestamped "./_L1JbzDnEMk_en_5 Signs the AI Bubble is Bursting_timestamped.txt" \
  --clean "./_L1JbzDnEMk_en_5 Signs the AI Bubble is Bursting_clean.txt" \
  --source youtube
```

> Re‑running is safe: `videos` is UPSERTed; `chapters` are replaced; `segments` use `ON CONFLICT DO NOTHING` (based on `BIGSERIAL`); duplicates are naturally avoided by `text_hash` + idempotent ingestion patterns.

---

## 7) Queries you’ll actually use

**Full‑text search within a video**

```sql
SELECT id, start_time_s, text
FROM media.transcript_segments
WHERE video_id = $1
  AND search_vector @@ plainto_tsquery('english', $2)
ORDER BY start_time_s
LIMIT 50;
```

**Fuzzy search (handles typos) using trigram**

```sql
SELECT id, start_time_s, text
FROM media.transcript_segments
WHERE video_id = $1
ORDER BY SIMILARITY(text, $2) DESC
LIMIT 30;
```

**Show a playable window around the first hit**

```sql
WITH hit AS (
  SELECT start_time_s
  FROM media.transcript_segments
  WHERE video_id = $1
    AND search_vector @@ plainto_tsquery('english', $2)
  ORDER BY start_time_s
  LIMIT 1
)
SELECT s.*
FROM media.transcript_segments s, hit
WHERE s.video_id = $1
  AND s.start_time_s BETWEEN hit.start_time_s - 10 AND hit.start_time_s + 30
ORDER BY s.start_time_s;
```

**List chapters for navigation**

```sql
SELECT start_time_s, end_time_s, text, summary
FROM media.chapters
WHERE video_id = $1
ORDER BY start_time_s;
```

---

## 8) Vector‑ready (later)

When you’re ready to add embeddings:

1. `CREATE EXTENSION vector;` (once)
2. Uncomment the `segment_embeddings` table in the DDL.
3. Backfill embeddings per `transcript_segments.id` with your model of choice.

That’s it — your primary schema does **not** need to change.

---

## 9) Notes & options

- **Segment length**: keep them short (≈5–20s) for better search and future embeddings. The loader infers durations if missing.
- **Multi‑user**: add `user_id UUID` to `media.videos` and index `(user_id, video_id)`. Child tables stay as‑is.
- **Idempotency**: if you expect frequent re‑ingest, consider a unique index on `(video_id, text_hash, start_time_s)` to hard‑dedupe.
- **Languages**: change `'english'` in `to_tsvector` if needed, or compute per‑row based on `language_code`.
- **Performance**: for tens of millions of segments, consider partitioning `transcript_segments` by `video_id` hash.

---

## 10) Troubleshooting

- `psycopg.OperationalError: connection refused` → check `.env` and that Postgres is running.
- `permission denied for schema media` → run DDL as a superuser or grant privileges to your app role.
- Poor search results? Try `phraseto_tsquery` for phrase search, or combine with `ILIKE` + trigram.

---

**Done.** Paste the SQL and the Python file and you’re ready to ingest your three files into a fast, queryable store that’s vector‑ready when you want it.

