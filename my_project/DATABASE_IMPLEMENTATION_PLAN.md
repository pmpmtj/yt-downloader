# PostgreSQL Database Implementation Plan
## YouTube Downloader with Download Tracking - Multi-App Platform Ready

### 🎯 **Project Goals**
- Add PostgreSQL database to existing clean YouTube downloader package
- Track YouTube download metadata, file paths, status, errors, and full video metadata
- **Multi-app platform architecture**: Shared database with app-specific tables
- **Shared user management**: Platform users shared across all future apps (YouTube, Dictation, Calendar, etc.)
- Design for multi-user with shared user concept from start
- Maintain clean architecture and Django migration readiness
- Focus on YouTube download tracking, with platform-ready user system

### 🏗️ **Architecture Decision: Multi-App Platform with Shared Database**
- **Shared PostgreSQL database** for entire platform (YouTube, future Dictation, Calendar apps)
- **App-specific table prefixes** (`youtube_`, `dictation_`, `calendar_`, etc.)
- **Shared user management** (`platform_users` table used by all apps)
- **YouTube package includes database module** for its specific tables
- **Environment-based configuration** (.env with fallback to environment variables)
- **Anonymous user** for development simplicity
- **Django-ready schema** for future migration

---

## 📋 **Implementation Steps**

### **Phase 1: Database Foundation**
1. **Add database dependencies** to `pyproject.toml`
   - `sqlalchemy>=2.0.0`
   - `psycopg2-binary>=2.9.0`
   - `alembic>=1.13.0`
   - `python-dotenv>=1.0.0`

2. **Create database module structure**:
   ```
   my_project/src/my_project/database/
   ├── __init__.py              # Database connection setup
   ├── models.py                # SQLAlchemy models
   ├── operations.py            # CRUD operations
   ├── connection.py            # Database connection management
   └── migrations/              # Alembic migrations
       ├── alembic.ini
       ├── env.py
       └── versions/
   ```

3. **Environment configuration**:
   - Create `.env` file for database credentials
   - Update `config/app_config.json` with database settings
   - Environment variable fallback support

### **Phase 2: Database Schema**
4. **Core tables design**:
   - `platform_users` - Shared across ALL platform apps (YouTube, Dictation, Calendar, etc.)
   - `youtube_download_sessions` - Groups YouTube downloads by session UUID
   - `youtube_video_downloads` - Individual YouTube video metadata and tracking
   - `youtube_download_files` - Track YouTube audio/video/transcript files separately
   - `youtube_download_errors` - Track YouTube download failures, retries, error messages

5. **Key features**:
   - **Platform-wide user system** - Shared `platform_users` table for all apps
   - **YouTube-specific functionality** - All YouTube tables prefixed for clarity
   - **Multi-app ready** - Database structure supports future Dictation, Calendar apps
   - UUID primary keys throughout
   - Full YouTube metadata storage
   - Download status tracking (pending → downloading → completed/failed)
   - File path tracking with status (exists/deleted/moved)
   - Error logging with retry counting
   - Transcript content storage for future AI analysis

### **Phase 3: Integration**
6. **Database operations module**:
   - `get_or_create_platform_user()` - Shared user management for all apps
   - `create_youtube_download_session()` - Start new YouTube download session
   - `log_youtube_video_metadata()` - Store YouTube video info
   - `track_youtube_download_progress()` - Update YouTube download status
   - `log_youtube_download_completion()` - Record successful YouTube downloads
   - `log_youtube_download_error()` - Record YouTube download failures and retries
   - `get_youtube_download_history()` - Query past YouTube downloads

7. **CLI integration**:
   - **Optional database logging** (can be disabled)
   - Automatic session creation and logging
   - Error tracking during downloads
   - No user interaction required (anonymous user)

### **Phase 4: Configuration**
8. **Environment setup**:
   ```bash
   # .env file - Platform-wide database
   PLATFORM_DB_HOST=localhost
   PLATFORM_DB_PORT=5432
   PLATFORM_DB_NAME=platform_db
   PLATFORM_DB_USER=platform_user
   PLATFORM_DB_PASSWORD=your_password
   PLATFORM_DB_ENABLED=true
   
   # App-specific settings
   YOUTUBE_APP_ENABLED=true
   ```

9. **PostgreSQL setup instructions**:
   - Local PostgreSQL installation
   - Database and user creation
   - Initial migration execution
   - Testing connection

---

## 🗄️ **Database Schema Design**

### **Platform Users Table** (Shared across ALL apps)
```sql
-- SHARED TABLE: Used by YouTube, Dictation, Calendar, and all future apps
CREATE TABLE platform_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    display_name VARCHAR(255),
    is_anonymous BOOLEAN DEFAULT false,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Platform-wide user metadata
    total_storage_used BIGINT DEFAULT 0,  -- Across all apps
    subscription_tier VARCHAR(50) DEFAULT 'free',  -- Future: Premium features
    last_active_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create anonymous user for development
INSERT INTO platform_users (email, display_name, is_anonymous) 
VALUES ('anonymous@localhost', 'Anonymous User', true);
```

### **YouTube Download Sessions Table** (YouTube-specific)
```sql
-- YOUTUBE-SPECIFIC: Groups YouTube downloads by session
CREATE TABLE youtube_download_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES platform_users(id) ON DELETE CASCADE,
    session_uuid VARCHAR(255) NOT NULL,  -- Current UUID system
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    status VARCHAR(50) DEFAULT 'in_progress',
    total_videos INTEGER DEFAULT 0,
    successful_downloads INTEGER DEFAULT 0,
    failed_downloads INTEGER DEFAULT 0,
    
    -- YouTube-specific session metadata
    base_download_directory TEXT,  -- Where files are stored for this session
    cli_arguments JSONB,           -- Store CLI args used for this session
    youtube_api_calls INTEGER DEFAULT 0  -- Track API usage
);
```

### **YouTube Video Downloads Table** (YouTube-specific metadata)
```sql
-- YOUTUBE-SPECIFIC: Individual YouTube video metadata and tracking
CREATE TABLE youtube_video_downloads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES youtube_download_sessions(id) ON DELETE CASCADE,
    user_id UUID REFERENCES platform_users(id) ON DELETE CASCADE,
    
    -- YouTube metadata
    url VARCHAR(500) NOT NULL,
    video_id VARCHAR(100),
    title TEXT,
    description TEXT,
    uploader VARCHAR(255),
    uploader_id VARCHAR(100),
    duration INTEGER,  -- seconds
    view_count BIGINT,
    like_count BIGINT,
    upload_date DATE,
    
    -- Download tracking
    download_started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    download_completed_at TIMESTAMP,
    status VARCHAR(50) DEFAULT 'pending',  -- pending, downloading, completed, failed
    retry_count INTEGER DEFAULT 0,
    
    -- YouTube-specific format selection
    selected_audio_format VARCHAR(50),
    selected_video_format VARCHAR(50),
    selected_video_quality VARCHAR(50),
    selected_transcript_language VARCHAR(10),
    available_formats JSONB,  -- Store all available formats for analysis
    
    -- YouTube-specific content for future AI analysis
    transcript_content TEXT,
    ai_summary TEXT,
    youtube_tags TEXT[],  -- YouTube video tags
    youtube_categories TEXT[],  -- YouTube categories
    
    -- Storage tracking
    total_file_size BIGINT,  -- Combined size of all downloaded files
    estimated_disk_space BIGINT  -- Predicted space needed
);
```

### **YouTube Download Files Table** (Track individual YouTube files)
```sql
-- YOUTUBE-SPECIFIC: Track individual YouTube download files
CREATE TABLE youtube_download_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_download_id UUID REFERENCES youtube_video_downloads(id) ON DELETE CASCADE,
    file_type VARCHAR(20) NOT NULL,  -- 'audio', 'video', 'transcript'
    file_path TEXT NOT NULL,
    file_size BIGINT,
    file_format VARCHAR(50),
    download_started_at TIMESTAMP,
    download_completed_at TIMESTAMP,
    status VARCHAR(50) DEFAULT 'pending',  -- pending, downloading, completed, failed, deleted
    checksum VARCHAR(64),  -- For integrity checking
    
    -- YouTube-specific file metadata
    youtube_format_id VARCHAR(20),  -- YouTube's internal format ID
    codec VARCHAR(50),             -- Video/audio codec used
    bitrate INTEGER,               -- File bitrate
    resolution VARCHAR(20),        -- Video resolution (e.g., "1920x1080")
    fps INTEGER,                   -- Video frame rate
    
    -- File management
    original_filename TEXT,        -- Original yt-dlp filename
    user_renamed_to TEXT,         -- If user renames file
    file_moved_to TEXT,           -- If file is moved
    is_deleted BOOLEAN DEFAULT false,
    deleted_at TIMESTAMP
);
```

### **YouTube Download Errors Table** (Track YouTube-specific failures)
```sql
-- YOUTUBE-SPECIFIC: Track YouTube download failures and errors
CREATE TABLE youtube_download_errors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_download_id UUID REFERENCES youtube_video_downloads(id) ON DELETE CASCADE,
    error_type VARCHAR(100),  -- 'network', 'format', 'permission', 'youtube_api', etc.
    error_message TEXT,
    error_details JSONB,  -- Full error context
    occurred_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    retry_attempt INTEGER,
    resolved BOOLEAN DEFAULT false,
    
    -- YouTube-specific error context
    youtube_error_code VARCHAR(50),    -- YouTube API error codes
    yt_dlp_error_type VARCHAR(100),    -- yt-dlp specific error types
    failed_format_id VARCHAR(20),     -- Which format failed
    network_response_code INTEGER,    -- HTTP response codes
    suggested_solution TEXT           -- Automated suggestions for fixing
);
```

### **Future App Tables Preview** (Not implemented yet, but shows structure)

#### **Dictation App Tables** (Future implementation)
```sql
-- DICTATION-SPECIFIC TABLES: Voice recording and transcription service
-- CREATE TABLE dictation_sessions (
--     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
--     user_id UUID REFERENCES platform_users(id) ON DELETE CASCADE,
--     session_name VARCHAR(255),
--     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
--     completed_at TIMESTAMP,
--     status VARCHAR(50) DEFAULT 'in_progress',  -- in_progress, completed, failed
--     total_recordings INTEGER DEFAULT 0,
--     total_duration INTEGER DEFAULT 0,  -- seconds
--     cloud_service VARCHAR(50),  -- aws, gcp, azure, etc.
--     upload_directory TEXT
-- );

-- CREATE TABLE dictation_recordings (
--     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
--     session_id UUID REFERENCES dictation_sessions(id) ON DELETE CASCADE,
--     user_id UUID REFERENCES platform_users(id) ON DELETE CASCADE,
--     
--     -- Recording metadata
--     original_filename TEXT NOT NULL,
--     file_path TEXT,
--     file_size BIGINT,
--     duration INTEGER,  -- seconds
--     audio_format VARCHAR(20),  -- wav, mp3, m4a, etc.
--     sample_rate INTEGER,
--     channels INTEGER,  -- mono=1, stereo=2
--     
--     -- Processing tracking
--     recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
--     uploaded_at TIMESTAMP,
--     transcribed_at TIMESTAMP,
--     status VARCHAR(50) DEFAULT 'recorded',  -- recorded, uploading, uploaded, transcribing, completed, failed
--     
--     -- Cloud service details
--     cloud_service VARCHAR(50),
--     cloud_file_url TEXT,
--     cloud_file_id VARCHAR(255),
--     
--     -- Transcription results
--     transcription_text TEXT,
--     transcription_confidence DECIMAL(3,2),  -- 0.00 to 1.00
--     language_detected VARCHAR(10),
--     error_message TEXT
-- );

-- CREATE TABLE dictation_transcripts (
--     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
--     recording_id UUID REFERENCES dictation_recordings(id) ON DELETE CASCADE,
--     user_id UUID REFERENCES platform_users(id) ON DELETE CASCADE,
--     
--     -- Transcript metadata
--     transcript_text TEXT NOT NULL,
--     confidence_score DECIMAL(3,2),
--     language VARCHAR(10),
--     service_used VARCHAR(50),  -- whisper, azure, gcp, aws, etc.
--     
--     -- Processing details
--     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
--     processing_time INTEGER,  -- milliseconds
--     word_count INTEGER,
--     
--     -- User editing
--     user_edited_text TEXT,  -- If user corrects the transcript
--     edited_at TIMESTAMP,
--     is_final BOOLEAN DEFAULT false,
--     
--     -- AI enhancement
--     ai_summary TEXT,
--     ai_tags TEXT[],
--     ai_sentiment VARCHAR(20)  -- positive, negative, neutral
-- );
```

#### **Calendar Dictation App Tables** (Future implementation)
```sql
-- CALENDAR-SPECIFIC TABLES: Voice-controlled calendar management
-- CREATE TABLE calendar_events (
--     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
--     user_id UUID REFERENCES platform_users(id) ON DELETE CASCADE,
--     
--     -- Event details
--     title VARCHAR(255) NOT NULL,
--     description TEXT,
--     event_date DATE NOT NULL,
--     start_time TIME,
--     end_time TIME,
--     timezone VARCHAR(50) DEFAULT 'UTC',
--     
--     -- Event metadata
--     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
--     updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
--     created_by_dictation BOOLEAN DEFAULT false,  -- If created via voice
--     dictation_recording_id UUID,  -- Link to dictation_recordings if voice-created
--     
--     -- Event status
--     status VARCHAR(50) DEFAULT 'scheduled',  -- scheduled, cancelled, completed
--     reminder_set BOOLEAN DEFAULT false,
--     reminder_time INTERVAL,  -- e.g., '1 hour', '30 minutes'
--     
--     -- Integration
--     external_calendar_id VARCHAR(255),  -- Google Calendar, Outlook, etc.
--     sync_status VARCHAR(50) DEFAULT 'local'  -- local, synced, sync_failed
-- );

-- CREATE TABLE calendar_dictations (
--     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
--     user_id UUID REFERENCES platform_users(id) ON DELETE CASCADE,
--     event_id UUID REFERENCES calendar_events(id) ON DELETE CASCADE,
--     recording_id UUID REFERENCES dictation_recordings(id) ON DELETE CASCADE,
--     
--     -- Dictation specifics for calendar
--     voice_command_type VARCHAR(50),  -- create_event, update_event, delete_event, query_schedule
--     original_voice_text TEXT,  -- What the user said
--     interpreted_action TEXT,  -- What the AI understood
--     
--     -- Processing results
--     processing_successful BOOLEAN DEFAULT false,
--     confidence_score DECIMAL(3,2),
--     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
--     
--     -- User confirmation
--     user_confirmed BOOLEAN DEFAULT false,
--     user_corrections TEXT,  -- If user made changes
--     final_action_taken TEXT  -- What actually happened
-- );

-- CREATE TABLE calendar_reminders (
--     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
--     event_id UUID REFERENCES calendar_events(id) ON DELETE CASCADE,
--     user_id UUID REFERENCES platform_users(id) ON DELETE CASCADE,
--     
--     -- Reminder details
--     reminder_time TIMESTAMP NOT NULL,
--     reminder_type VARCHAR(50) DEFAULT 'notification',  -- notification, email, sms, voice
--     message TEXT,
--     
--     -- Status tracking
--     sent_at TIMESTAMP,
--     status VARCHAR(50) DEFAULT 'pending',  -- pending, sent, failed
--     delivery_method VARCHAR(50),  -- push, email, sms, voice_call
--     
--     -- User interaction
--     acknowledged_at TIMESTAMP,
--     user_action VARCHAR(50),  -- dismissed, snoozed, marked_done
--     snooze_until TIMESTAMP
-- );
```

#### **Cross-App Analytics Tables** (Future implementation)
```sql
-- PLATFORM-WIDE ANALYTICS: Query across all apps
-- CREATE TABLE user_activity_summary (
--     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
--     user_id UUID REFERENCES platform_users(id) ON DELETE CASCADE,
--     date DATE NOT NULL,
--     
--     -- YouTube activity
--     youtube_videos_downloaded INTEGER DEFAULT 0,
--     youtube_storage_used BIGINT DEFAULT 0,
--     youtube_transcripts_analyzed INTEGER DEFAULT 0,
--     
--     -- Dictation activity
--     dictation_recordings_made INTEGER DEFAULT 0,
--     dictation_minutes_recorded INTEGER DEFAULT 0,
--     dictation_words_transcribed INTEGER DEFAULT 0,
--     
--     -- Calendar activity
--     calendar_events_created INTEGER DEFAULT 0,
--     calendar_voice_commands INTEGER DEFAULT 0,
--     calendar_reminders_sent INTEGER DEFAULT 0,
--     
--     -- Cross-app totals
--     total_storage_used BIGINT DEFAULT 0,
--     total_ai_api_calls INTEGER DEFAULT 0,
--     last_active_app VARCHAR(50)
-- );
```

---

## 🔧 **Implementation Configuration**

### **Platform Database Connection (.env)**
```bash
# Platform-Wide Database Configuration
PLATFORM_DB_HOST=localhost
PLATFORM_DB_PORT=5432
PLATFORM_DB_NAME=platform_db
PLATFORM_DB_USER=platform_user
PLATFORM_DB_PASSWORD=secure_password
PLATFORM_DB_ENABLED=true

# App-Specific Settings
YOUTUBE_APP_ENABLED=true
YOUTUBE_APP_NAME=youtube_downloader
YOUTUBE_APP_VERSION=0.1.0

# Future Apps (Not implemented yet)
DICTATION_APP_ENABLED=false
CALENDAR_APP_ENABLED=false

# Optional: Connection pool settings
PLATFORM_DB_POOL_SIZE=5
PLATFORM_DB_MAX_OVERFLOW=10
```

### **App Configuration Update**
```json
{
    "database": {
        "enabled": true,
        "auto_log_downloads": true,
        "log_errors": true,
        "log_file_operations": true,
        "anonymous_user_email": "anonymous@localhost",
        "table_prefix": "youtube_",
        "app_name": "youtube_downloader"
    },
    "downloads": {
        "base_directory": "downloads",
        "create_session_folders": true,
        "create_video_folders": true,
        "folder_structure": "{session_uuid}/{video_uuid}/{media_type}"
    }
    // ... existing config
}
```

### **CLI Integration Points**
```python
# In core_CLI.py - Automatic database logging
def process_single_video(url: str, session_uuid: str, base_downloads_dir: str, args) -> dict:
    # 1. Get/create platform user (shared across all apps)
    platform_user = get_or_create_platform_user("anonymous@localhost")
    
    # 2. Create YouTube download session
    youtube_session = create_youtube_download_session(session_uuid, platform_user.id)
    
    # 3. Log YouTube video metadata
    video_record = log_youtube_video_metadata(url, video_info, youtube_session.id, platform_user.id)
    
    # 4. Track YouTube download attempts
    if args.audio:
        track_youtube_download_start(video_record.id, 'audio', selected_format)
        # ... download logic ...
        track_youtube_download_completion(video_record.id, 'audio', file_path, success)
    
    # 5. Log YouTube-specific errors
    if error:
        log_youtube_download_error(video_record.id, error_type, error_message, yt_dlp_context)
```

---

## 📦 **PostgreSQL Setup Instructions**

### **1. Install PostgreSQL**
```bash
# Windows (using chocolatey)
choco install postgresql

# Or download from: https://www.postgresql.org/download/windows/
```

### **2. Create Platform Database and User**
```sql
-- Connect as postgres superuser
createdb platform_db
createuser platform_user
\password platform_user

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE platform_db TO platform_user;
ALTER USER platform_user CREATEDB;  -- For running tests

-- Future: Other apps will use the same database and user
-- No need to create separate databases for Dictation, Calendar apps
```

### **3. Test Platform Database Connection**
```python
# Test script
from sqlalchemy import create_engine
engine = create_engine('postgresql://platform_user:password@localhost/platform_db')
print("Platform database connection successful!" if engine.connect() else "Connection failed!")
```

---

## 🎯 **Next Steps After Implementation**

### **Immediate Testing**
1. **Platform database connection** - Verify PostgreSQL connectivity
2. **Migration execution** - Run initial schema creation (all YouTube tables + shared user table)
3. **Anonymous platform user creation** - Verify default user exists in platform_users table
4. **YouTube download logging** - Test with real YouTube URL
5. **YouTube error tracking** - Test with invalid YouTube URL
6. **Multi-app readiness** - Verify table structure supports future apps

### **Future Enhancements** (Next conversations)
1. **Platform user management** - Add family member support across all apps
2. **YouTube query interface** - Search and filter YouTube downloads
3. **File management** - Track moved/deleted YouTube files
4. **YouTube transcript analysis** - AI summaries and search of YouTube content
5. **Django migration** - Seamless web interface integration
6. **Add Dictation app** - New tables: dictation_sessions, dictation_recordings, etc.
7. **Add Calendar app** - New tables: calendar_events, calendar_dictations, etc.
8. **Cross-app analytics** - Query data across YouTube, Dictation, Calendar apps

### **Django Migration Readiness**
- **Platform-wide schema** designed for Django compatibility
- **Shared user table** ready for Django User integration across all apps
- **App-specific models** easily translatable to Django ORM
- **Multi-app Django project** ready (YouTube app, Dictation app, Calendar app)
- Data migration scripts prepared for entire platform

---

## ✅ **Implementation Checklist**

- [ ] Add database dependencies to pyproject.toml
- [ ] Create database module structure
- [ ] Design and implement SQLAlchemy models
- [ ] Set up Alembic migrations
- [ ] Create database connection management
- [ ] Implement CRUD operations
- [ ] Add environment variable support
- [ ] Integrate with CLI download flow
- [ ] Create PostgreSQL setup instructions
- [ ] Test with real downloads
- [ ] Document usage and troubleshooting

---

## 🚨 **Important Notes**

1. **Database is OPTIONAL** - YouTube tool works without database if disabled
2. **Shared platform users** - `platform_users` table shared across ALL future apps
3. **YouTube-specific tables** - All YouTube functionality uses `youtube_` prefixed tables
4. **Anonymous user** - No authentication required during development
5. **Clean separation** - Database module completely separate from core YouTube logic
6. **Multi-app ready** - Database structure supports Dictation, Calendar, and future apps
7. **Django ready** - Schema and models designed for easy Django migration of entire platform
8. **Scalable architecture** - Each app adds its own table group without conflicts

---

**This plan maintains your clean architecture while adding powerful YouTube download tracking capabilities AND sets up the foundation for your entire multi-app platform (Dictation, Calendar, etc.). The shared user system and app-specific table structure ensures clean separation while enabling cross-app functionality. Ready to start implementation in the next conversation!**
