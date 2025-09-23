# transcriptions_dl/tests.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from unittest.mock import patch, MagicMock

User = get_user_model()


class TranscriptDownloadAPITestCase(APITestCase):
    """Test cases for transcript download API endpoints."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        
        self.test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        self.invalid_url = "https://invalid-url.com"
    
    def test_download_transcript_sync_success(self):
        """Test successful synchronous transcript download."""
        with patch('transcriptions_dl.api.download_transcript_files') as mock_download:
            mock_download.return_value = True
            
            with patch('transcriptions_dl.api.get_video_info') as mock_video_info:
                mock_video_info.return_value = {
                    'id': 'dQw4w9WgXcQ',
                    'title': 'Test Video',
                    'uploader': 'Test Channel',
                    'duration': 212
                }
                
                with patch('transcriptions_dl.api._find_transcript_files') as mock_find_files:
                    mock_find_files.return_value = {
                        'clean': '/path/to/clean.txt',
                        'timestamped': '/path/to/timestamped.txt',
                        'structured': '/path/to/structured.json'
                    }
                    
                    response = self.client.post('/api/transcriptions/download/', {
                        'url': self.test_url,
                        'download_to_remote': False
                    })
                    
                    self.assertEqual(response.status_code, status.HTTP_200_OK)
                    self.assertTrue(response.data['success'])
                    self.assertIn('file_paths', response.data)
    
    def test_download_transcript_invalid_url(self):
        """Test transcript download with invalid URL."""
        response = self.client.post('/api/transcriptions/download/', {
            'url': self.invalid_url
        })
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Invalid YouTube URL', response.data['detail'])
    
    def test_download_transcript_missing_url(self):
        """Test transcript download with missing URL."""
        response = self.client.post('/api/transcriptions/download/', {})
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Missing \'url\'', response.data['detail'])
    
    def test_download_transcript_async(self):
        """Test asynchronous transcript download."""
        with patch('transcriptions_dl.api.process_transcript_download') as mock_task:
            response = self.client.post('/api/transcriptions/download-async/', {
                'url': self.test_url
            })
            
            self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
            self.assertIn('task_id', response.data)
            self.assertEqual(response.data['status'], 'queued')
    
    def test_transcript_preview_success(self):
        """Test transcript preview functionality."""
        with patch('transcriptions_dl.api.get_video_info') as mock_video_info:
            mock_video_info.return_value = {
                'id': 'dQw4w9WgXcQ',
                'title': 'Test Video',
                'uploader': 'Test Channel',
                'duration': 212
            }
            
            with patch('transcriptions_dl.api.preview_transcript') as mock_preview:
                mock_preview.return_value = {
                    'preview_text': 'Sample transcript text...',
                    'total_entries': 100,
                    'statistics': {
                        'word_count': 500,
                        'character_count': 2500
                    }
                }
                
                response = self.client.get('/api/transcriptions/preview/', {
                    'url': self.test_url
                })
                
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertTrue(response.data['success'])
                self.assertIn('transcript_preview', response.data)
    
    def test_transcript_preview_no_transcript(self):
        """Test transcript preview when no transcript is available."""
        with patch('transcriptions_dl.api.get_video_info') as mock_video_info:
            mock_video_info.return_value = {
                'id': 'dQw4w9WgXcQ',
                'title': 'Test Video'
            }
            
            with patch('transcriptions_dl.api.preview_transcript') as mock_preview:
                mock_preview.return_value = None
                
                response = self.client.get('/api/transcriptions/preview/', {
                    'url': self.test_url
                })
                
                self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
                self.assertIn('No transcript available', response.data['detail'])
    
    def test_transcript_job_status_placeholder(self):
        """Test job status endpoint (placeholder implementation)."""
        response = self.client.get('/api/transcriptions/status/test-job-id/')
        
        self.assertEqual(response.status_code, status.HTTP_501_NOT_IMPLEMENTED)
        self.assertIn('not implemented yet', response.data['detail'])
    
    def test_transcript_job_result_placeholder(self):
        """Test job result endpoint (placeholder implementation)."""
        response = self.client.get('/api/transcriptions/result/test-job-id/')
        
        self.assertEqual(response.status_code, status.HTTP_501_NOT_IMPLEMENTED)
        self.assertIn('not implemented yet', response.data['detail'])
    
    def test_unauthenticated_access(self):
        """Test that unauthenticated users cannot access endpoints."""
        self.client.force_authenticate(user=None)
        
        response = self.client.post('/api/transcriptions/download/', {
            'url': self.test_url
        })
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TranscriptDownloadTaskTestCase(TestCase):
    """Test cases for background tasks."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
    
    @patch('transcriptions_dl.tasks.download_transcript_files')
    @patch('transcriptions_dl.tasks.get_video_info')
    def test_process_transcript_download_success(self, mock_video_info, mock_download):
        """Test successful background transcript processing."""
        mock_download.return_value = True
        mock_video_info.return_value = {
            'title': 'Test Video',
            'uploader': 'Test Channel'
        }
        
        # This would normally be called by the background task system
        from transcriptions_dl.tasks import process_transcript_download
        
        # Test the function directly (not through background task system)
        process_transcript_download(
            url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            task_id="test-task-id",
            output_dir="/tmp/test",
            user_id=self.user.id,
            user_ip="127.0.0.1",
            user_agent="Test Agent"
        )
        
        mock_download.assert_called_once()
        mock_video_info.assert_called_once()
    
    @patch('transcriptions_dl.tasks.download_transcript_files')
    def test_process_transcript_download_failure(self, mock_download):
        """Test background transcript processing failure."""
        mock_download.return_value = False
        
        from transcriptions_dl.tasks import process_transcript_download
        
        # Test the function directly
        process_transcript_download(
            url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            task_id="test-task-id",
            output_dir="/tmp/test",
            user_id=self.user.id
        )
        
        mock_download.assert_called_once()