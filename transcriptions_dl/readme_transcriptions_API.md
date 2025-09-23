# Transcriptions API Documentation

A Django REST API for downloading YouTube video transcripts in multiple formats optimized for LLM analysis.

## Overview

The Transcriptions API provides endpoints to download YouTube video transcripts in 3 different formats:
- **Clean Text** - Optimized for LLM analysis with filler words removed
- **Timestamped Text** - Original format with timestamps for each segment  
- **Structured JSON** - Rich metadata with chapters, statistics, and analysis

## API Endpoints

### 1. Synchronous Transcript Download
**POST** `/transcriptions/api/download/`

Downloads transcript files immediately and returns file paths.

**Request Body:**
```json
{
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "download_to_remote": false
}
```

**Response (Success):**
```json
{
    "success": true,
    "message": "Transcript files downloaded successfully to server",
    "video_info": {
        "title": "Video Title",
        "uploader": "Channel Name",
        "duration": 212,
        "video_id": "dQw4w9WgXcQ"
    },
    "file_paths": {
        "clean": "/path/to/video_clean.txt",
        "timestamped": "/path/to/video_timestamped.txt",
        "structured": "/path/to/video_structured.json"
    },
    "download_source": "api"
}
```

### 2. Asynchronous Transcript Download
**POST** `/transcriptions/api/download-async/`

Queues a background task for transcript download.

**Request Body:**
```json
{
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
}
```

**Response:**
```json
{
    "task_id": "uuid-task-id",
    "status": "queued",
    "status_url": "http://localhost:8000/transcriptions/api/status/uuid-task-id/",
    "result_url": "http://localhost:8000/transcriptions/api/result/uuid-task-id/"
}
```

### 3. Transcript Preview
**GET** `/transcriptions/api/preview/?url=YOUTUBE_URL`

Preview transcript content before downloading.

**Response:**
```json
{
    "success": true,
    "video_info": {
        "title": "Video Title",
        "uploader": "Channel Name",
        "duration": 212,
        "video_id": "dQw4w9WgXcQ"
    },
    "transcript_preview": {
        "preview_text": "[0.00s] Sample transcript text...",
        "total_entries": 100,
        "statistics": {
            "word_count": 500,
            "character_count": 2500,
            "estimated_reading_time_minutes": 2.5
        }
    }
}
```

### 4. Job Status (Placeholder)
**GET** `/transcriptions/api/status/{job_id}/`

Check status of async download job.

**Response:**
```json
{
    "detail": "Status checking not implemented yet - requires database integration"
}
```

### 5. Job Result (Placeholder)
**GET** `/transcriptions/api/result/{job_id}/`

Retrieve result of completed async download.

**Response:**
```json
{
    "detail": "Result retrieval not implemented yet - requires database integration"
}
```

## PowerShell Testing Commands

### Prerequisites
- Django server running on `localhost:8000`
- Valid authentication (replace `YOUR_TOKEN` with your actual token)

### 1. Test Synchronous Download
```powershell
# Test sync download (server storage)
$body = @{
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    download_to_remote = $false
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/transcriptions/api/download/" -Method POST -Body $body -ContentType "application/json" -Headers @{"Authorization" = "Bearer YOUR_TOKEN"}
```

### 2. Test Asynchronous Download
```powershell
# Test async download (background task)
$body = @{
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/transcriptions/api/download-async/" -Method POST -Body $body -ContentType "application/json" -Headers @{"Authorization" = "Bearer YOUR_TOKEN"}
```

### 3. Test Transcript Preview
```powershell
# Test transcript preview
Invoke-RestMethod -Uri "http://localhost:8000/transcriptions/api/preview/?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ" -Method GET -Headers @{"Authorization" = "Bearer YOUR_TOKEN"}
```

### 4. Test with Session Authentication
```powershell
# If using session authentication instead of token
$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession

# Login first to get session cookie
$loginBody = @{
    email = "your-email@example.com"
    password = "your-password"
} | ConvertTo-Json

$loginResponse = Invoke-RestMethod -Uri "http://localhost:8000/accounts/login/" -Method POST -Body $loginBody -ContentType "application/json" -WebSession $session

# Then use the session for API calls
$body = @{
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    download_to_remote = $false
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/transcriptions/api/download/" -Method POST -Body $body -ContentType "application/json" -WebSession $session
```

### 5. Test Error Cases
```powershell
# Test with invalid URL
$body = @{
    url = "https://invalid-url.com"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/transcriptions/api/download/" -Method POST -Body $body -ContentType "application/json" -Headers @{"Authorization" = "Bearer YOUR_TOKEN"}

# Test with missing URL
$body = @{} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/transcriptions/api/download/" -Method POST -Body $body -ContentType "application/json" -Headers @{"Authorization" = "Bearer YOUR_TOKEN"}
```

## Complete Test Script

```powershell
# Set your base URL and authentication
$baseUrl = "http://localhost:8000"
$headers = @{"Authorization" = "Bearer YOUR_TOKEN"}  # Replace with your auth method

# Test URL
$testUrl = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

Write-Host "Testing Transcript API Endpoints..." -ForegroundColor Green

# 1. Test Preview
Write-Host "`n1. Testing Preview..." -ForegroundColor Yellow
try {
    $previewResponse = Invoke-RestMethod -Uri "$baseUrl/transcriptions/api/preview/?url=$testUrl" -Method GET -Headers $headers
    Write-Host "Preview Success: $($previewResponse.success)" -ForegroundColor Green
} catch {
    Write-Host "Preview Error: $($_.Exception.Message)" -ForegroundColor Red
}

# 2. Test Sync Download
Write-Host "`n2. Testing Sync Download..." -ForegroundColor Yellow
try {
    $body = @{
        url = $testUrl
        download_to_remote = $false
    } | ConvertTo-Json
    
    $syncResponse = Invoke-RestMethod -Uri "$baseUrl/transcriptions/api/download/" -Method POST -Body $body -ContentType "application/json" -Headers $headers
    Write-Host "Sync Download Success: $($syncResponse.success)" -ForegroundColor Green
    Write-Host "File Paths: $($syncResponse.file_paths | ConvertTo-Json)" -ForegroundColor Cyan
} catch {
    Write-Host "Sync Download Error: $($_.Exception.Message)" -ForegroundColor Red
}

# 3. Test Async Download
Write-Host "`n3. Testing Async Download..." -ForegroundColor Yellow
try {
    $body = @{
        url = $testUrl
    } | ConvertTo-Json
    
    $asyncResponse = Invoke-RestMethod -Uri "$baseUrl/transcriptions/api/download-async/" -Method POST -Body $body -ContentType "application/json" -Headers $headers
    Write-Host "Async Download Success: $($asyncResponse.status)" -ForegroundColor Green
    Write-Host "Task ID: $($asyncResponse.task_id)" -ForegroundColor Cyan
} catch {
    Write-Host "Async Download Error: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`nTesting Complete!" -ForegroundColor Green
```

## Error Responses

### 400 Bad Request
```json
{
    "detail": "Missing 'url'"
}
```

### 400 Bad Request - Invalid URL
```json
{
    "detail": "Invalid YouTube URL"
}
```

### 400 Bad Request - Bot Detection
```json
{
    "detail": "YouTube requires authentication for this request. Please upload your YouTube cookies using the Cookie Management page."
}
```

### 401 Unauthorized
```json
{
    "detail": "Authentication credentials were not provided."
}
```

### 404 Not Found - No Transcript
```json
{
    "detail": "No transcript available for this video"
}
```

### 501 Not Implemented - Placeholder Endpoints
```json
{
    "detail": "Status checking not implemented yet - requires database integration"
}
```

## Features

### Smart Transcript Selection
- Prioritizes manual transcripts over auto-generated
- English language preferred
- Automatic fallback to available languages

### Text Processing
- Filler word removal (`um`, `uh`, `like`, etc.)
- Whitespace normalization
- Transcription artifact fixing
- Chapter detection based on silence gaps

### File Formats
1. **Clean Text** (`*_clean.txt`) - LLM-optimized format
2. **Timestamped Text** (`*_timestamped.txt`) - Original format with timestamps
3. **Structured JSON** (`*_structured.json`) - Rich metadata and analysis

### Security
- Authentication required for all endpoints
- User-specific download directories
- IP and user agent tracking
- Cookie integration for YouTube authentication

## Integration

The API integrates with your existing:
- `core.downloaders.transcriptions` module
- User authentication system
- Logging and security utilities
- Cookie management system

## File Naming Convention

Files are named using the pattern:
```
{video_id}_{language_code}_{safe_title}_{format}.{extension}
```

Example:
```
dQw4w9WgXcQ_en_Rick Astley - Never Gonna Give You Up Official Vid_clean.txt
dQw4w9WgXcQ_en_Rick Astley - Never Gonna Give You Up Official Vid_timestamped.txt
dQw4w9WgXcQ_en_Rick Astley - Never Gonna Give You Up Official Vid_structured.json
```

## Notes

- **Database Integration**: Status and result endpoints are placeholders until database models are added
- **User Directories**: Files are saved to user-specific directories
- **Background Tasks**: Async downloads use `django-background-tasks`
- **Error Handling**: Comprehensive error responses with helpful guidance
- **Authentication**: Supports both token and session-based authentication

## Search API Endpoints

### 6. Search Transcripts
**GET** `/transcriptions/api/search/`

Search across all downloaded transcripts with advanced filtering and pagination.

**Query Parameters:**
- `q` - Search query text
- `type` - Search type: `full_text` (default), `exact`, `fuzzy`
- `page` - Page number (default: 1)
- `page_size` - Results per page (default: 20, max: 100)
- `title` - Filter by video title
- `uploader` - Filter by channel/uploader
- `date_from` - Filter from date (YYYY-MM-DD)
- `date_to` - Filter to date (YYYY-MM-DD)
- `duration_min` - Minimum duration in seconds
- `duration_max` - Maximum duration in seconds
- `time_start` - Search within time range start (seconds)
- `time_end` - Search within time range end (seconds)
- `language` - Filter by language code
- `is_generated` - Filter by content type: `true` (auto-generated), `false` (manual)
- `sort` - Sort by: `relevance` (default), `date`, `duration`, `title`

**Example Request:**
```
GET /transcriptions/api/search/?q=AI&type=full_text&page=1&page_size=10&sort=relevance
```

**Response:**
```json
{
    "results": [
        {
            "video": {
                "video_id": "_L1JbzDnEMk",
                "title": "5 Signs the AI Bubble is Bursting",
                "duration_s": 400,
                "upload_date": "2025-01-30",
                "uploader": "Sabine Hossenfelder",
                "language_code": "en",
                "is_generated": true,
                "processed_at": "2025-09-22T16:35:41Z",
                "text_word_count": 996,
                "text_char_count": 5714,
                "chapters_count": 9,
                "segments_count": 152
            },
            "matching_segments": [
                {
                    "id": 1,
                    "start_time_s": 0.0,
                    "duration_s": 3.0,
                    "text": "Welcome to Sabine Hossenfelder...",
                    "is_generated": true,
                    "source": "youtube"
                }
            ],
            "total_segments": 152,
            "relevance_score": 1.0
        }
    ],
    "total_count": 1,
    "page": 1,
    "page_size": 20,
    "total_pages": 1,
    "has_next": false,
    "has_previous": false,
    "query": "AI",
    "search_type": "full_text",
    "filters_applied": {
        "video_filters": {},
        "time_range": null,
        "language": null,
        "is_generated": null
    }
}
```

### 7. Search Chapters
**GET** `/transcriptions/api/search/chapters/`

Search within video chapters.

**Query Parameters:**
- `q` - Search query text
- `video_id` - Filter by specific video ID
- `page` - Page number (default: 1)
- `page_size` - Results per page (default: 20, max: 100)

**Response:**
```json
{
    "results": [
        {
            "id": 1,
            "video_id": "_L1JbzDnEMk",
            "video_title": "5 Signs the AI Bubble is Bursting",
            "start_time_s": 0.0,
            "end_time_s": 41.0,
            "text": "Introduction to AI bubble discussion",
            "summary": "Overview of AI market trends",
            "duration_s": 41.0
        }
    ],
    "total_count": 1,
    "page": 1,
    "page_size": 20,
    "total_pages": 1,
    "has_next": false,
    "has_previous": false,
    "query": "AI"
}
```

### 8. Get Transcript Content
**GET** `/transcriptions/api/transcript/{video_id}/`

Get full transcript content for a specific video.

**Query Parameters:**
- `format` - Content format: `clean_text` (default), `timestamped`, `structured_json`

**Response:**
```json
{
    "video_id": "_L1JbzDnEMk",
    "title": "5 Signs the AI Bubble is Bursting",
    "format": "clean_text",
    "content": "Welcome to Sabine Hossenfelder...",
    "is_json": false,
    "stored_at": "2025-09-22T16:35:41Z",
    "language_code": "en",
    "is_generated": true
}
```

### 9. Search Suggestions
**GET** `/transcriptions/api/search/suggestions/`

Get search suggestions based on partial query.

**Query Parameters:**
- `q` - Partial search query (minimum 2 characters)
- `limit` - Maximum suggestions (default: 10, max: 50)

**Response:**
```json
{
    "suggestions": [
        "5 Signs the AI Bubble is Bursting",
        "artificial intelligence",
        "machine learning",
        "AI technology"
    ]
}
```

### 10. Search Statistics
**GET** `/transcriptions/api/search/stats/`

Get search statistics for the current user.

**Response:**
```json
{
    "total_videos": 1,
    "total_segments": 152,
    "total_chapters": 9,
    "languages": ["en"],
    "date_range": {
        "earliest": "2025-09-22T16:35:41Z",
        "latest": "2025-09-22T16:35:41Z"
    },
    "total_duration_s": 400
}
```

## PowerShell Testing Commands for Search

### 1. Test Basic Search
```powershell
# Search for "AI" across all transcripts
Invoke-RestMethod -Uri "http://localhost:8000/transcriptions/api/search/?q=AI" -Method GET -Headers @{"Authorization" = "Bearer YOUR_TOKEN"}
```

### 2. Test Advanced Search with Filters
```powershell
# Search with multiple filters
$searchParams = @{
    q = "machine learning"
    type = "full_text"
    page = 1
    page_size = 10
    sort = "relevance"
    language = "en"
    is_generated = "false"
} | ConvertTo-Json

$queryString = ($searchParams | ConvertFrom-Json | ForEach-Object { "$($_.Name)=$($_.Value)" }) -join "&"
Invoke-RestMethod -Uri "http://localhost:8000/transcriptions/api/search/?$queryString" -Method GET -Headers @{"Authorization" = "Bearer YOUR_TOKEN"}
```

### 3. Test Chapter Search
```powershell
# Search within chapters
Invoke-RestMethod -Uri "http://localhost:8000/transcriptions/api/search/chapters/?q=introduction" -Method GET -Headers @{"Authorization" = "Bearer YOUR_TOKEN"}
```

### 4. Test Search Suggestions
```powershell
# Get search suggestions
Invoke-RestMethod -Uri "http://localhost:8000/transcriptions/api/search/suggestions/?q=AI&limit=5" -Method GET -Headers @{"Authorization" = "Bearer YOUR_TOKEN"}
```

### 5. Test User Statistics
```powershell
# Get user search statistics
Invoke-RestMethod -Uri "http://localhost:8000/transcriptions/api/search/stats/" -Method GET -Headers @{"Authorization" = "Bearer YOUR_TOKEN"}
```

### 6. Test Transcript Content Retrieval
```powershell
# Get full transcript content
Invoke-RestMethod -Uri "http://localhost:8000/transcriptions/api/transcript/_L1JbzDnEMk/?format=clean_text" -Method GET -Headers @{"Authorization" = "Bearer YOUR_TOKEN"}
```

## Complete Search Test Script

```powershell
# Set your base URL and authentication
$baseUrl = "http://localhost:8000"
$headers = @{"Authorization" = "Bearer YOUR_TOKEN"}  # Replace with your auth method

Write-Host "Testing Search API Endpoints..." -ForegroundColor Green

# 1. Test Basic Search
Write-Host "`n1. Testing Basic Search..." -ForegroundColor Yellow
try {
    $searchResponse = Invoke-RestMethod -Uri "$baseUrl/transcriptions/api/search/?q=AI" -Method GET -Headers $headers
    Write-Host "Search Success: Found $($searchResponse.total_count) results" -ForegroundColor Green
} catch {
    Write-Host "Search Error: $($_.Exception.Message)" -ForegroundColor Red
}

# 2. Test Advanced Search
Write-Host "`n2. Testing Advanced Search..." -ForegroundColor Yellow
try {
    $advancedSearch = Invoke-RestMethod -Uri "$baseUrl/transcriptions/api/search/?q=machine&type=full_text&sort=date&page_size=5" -Method GET -Headers $headers
    Write-Host "Advanced Search Success: $($advancedSearch.total_count) results" -ForegroundColor Green
} catch {
    Write-Host "Advanced Search Error: $($_.Exception.Message)" -ForegroundColor Red
}

# 3. Test Chapter Search
Write-Host "`n3. Testing Chapter Search..." -ForegroundColor Yellow
try {
    $chapterSearch = Invoke-RestMethod -Uri "$baseUrl/transcriptions/api/search/chapters/?q=introduction" -Method GET -Headers $headers
    Write-Host "Chapter Search Success: $($chapterSearch.total_count) chapters found" -ForegroundColor Green
} catch {
    Write-Host "Chapter Search Error: $($_.Exception.Message)" -ForegroundColor Red
}

# 4. Test Search Suggestions
Write-Host "`n4. Testing Search Suggestions..." -ForegroundColor Yellow
try {
    $suggestions = Invoke-RestMethod -Uri "$baseUrl/transcriptions/api/search/suggestions/?q=AI&limit=5" -Method GET -Headers $headers
    Write-Host "Suggestions: $($suggestions.suggestions -join ', ')" -ForegroundColor Green
} catch {
    Write-Host "Suggestions Error: $($_.Exception.Message)" -ForegroundColor Red
}

# 5. Test User Statistics
Write-Host "`n5. Testing User Statistics..." -ForegroundColor Yellow
try {
    $stats = Invoke-RestMethod -Uri "$baseUrl/transcriptions/api/search/stats/" -Method GET -Headers $headers
    Write-Host "User Stats: $($stats.total_videos) videos, $($stats.total_segments) segments" -ForegroundColor Green
} catch {
    Write-Host "Stats Error: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`nSearch Testing Complete!" -ForegroundColor Green
```

## Search Features

### Full-Text Search
- **PostgreSQL Search Vectors**: Fast full-text search using database indexes
- **Multiple Search Types**: Full-text, exact match, and fuzzy search
- **Relevance Scoring**: Results ranked by relevance to search query

### Advanced Filtering
- **Video Metadata**: Filter by title, uploader, date range, duration
- **Content Type**: Filter by manual vs auto-generated transcripts
- **Language**: Filter by transcript language
- **Time Range**: Search within specific video segments

### Pagination & Sorting
- **Pagination**: Configurable page size with navigation
- **Sorting Options**: Relevance, date, duration, title
- **Result Highlighting**: Matching segments highlighted in results

### User Experience
- **Search Suggestions**: Auto-complete based on existing content
- **Statistics Dashboard**: User library overview
- **Responsive Interface**: Modern web interface with collapsible filters

## Next Steps

1. ✅ Add database models for job tracking
2. ✅ Implement status and result endpoints  
3. ✅ Add transcript search and filtering
4. Add file cleanup and management
5. Add batch processing capabilities
6. Add search analytics and trending topics
