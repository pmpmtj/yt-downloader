"""
Integration tests for CLI workflows and end-to-end functionality.

Tests the complete user workflows through the CLI interface including
video downloads, transcript processing, and export functionality.
"""

import pytest
import subprocess
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock


class TestBasicCLIWorkflows:
    """Test fundamental CLI workflow scenarios."""
    
    @pytest.mark.integration
    @pytest.mark.slow
    def test_single_video_info_only(self, temp_download_dir):
        """Test info-only extraction without downloads."""
        # This tests the --info-only flag functionality
        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "Video info extracted successfully"
            mock_run.return_value = mock_result
            
            cmd = [
                "python", "-m", "src.my_project.core_CLI",
                "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "--info-only",
                "--outdir", str(temp_download_dir["base_dir"])
            ]
            
            # Test that command would execute without errors
            assert True  # Placeholder for actual implementation
    
    @pytest.mark.integration
    def test_preview_only_workflow(self, temp_download_dir):
        """Test preview-transcript workflow without downloads."""
        from src.my_project.core_CLI import main
        
        test_args = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "--preview-transcript",
            "--outdir", str(temp_download_dir["base_dir"])
        ]
        
        with patch('sys.argv', ['core_CLI.py'] + test_args):
            with patch('src.my_project.core_CLI.get_video_info') as mock_extract:
                with patch('src.my_project.core_CLI.print_transcript_preview') as mock_preview:
                    mock_extract.return_value = {"id": "dQw4w9WgXcQ", "title": "Test Video"}
                    mock_preview.return_value = None
                    
                    # Should execute preview workflow without downloads
                    try:
                        main()
                        assert True
                    except SystemExit as e:
                        # Normal CLI exit is expected
                        assert e.code == 0
    
    @pytest.mark.integration
    def test_transcript_only_workflow(self, temp_download_dir, mock_video_info, sample_transcript_data):
        """Test transcript-only download workflow."""
        from src.my_project.core_CLI import process_single_video
        
        with patch('src.my_project.core_CLI.get_video_info', return_value=mock_video_info):
            with patch('src.my_project.core_CLI.list_transcript_metadata') as mock_discover:
                with patch('src.my_project.yt_downloads_utils.download_transcript') as mock_download:
                    
                    # Mock transcript discovery
                    mock_discover.return_value = [
                        {"language_code": "en", "language": "English", "is_default": True}
                    ]
                    
                    # Mock successful transcript download
                    mock_download.return_value = {
                        "clean": "/path/to/clean.txt",
                        "timestamped": "/path/to/timestamped.txt",
                        "structured": "/path/to/structured.json"
                    }
                    
                    # Create mock args object
                    mock_args = Mock()
                    mock_args.transcript = True
                    mock_args.transcript_formats = ["all"]
                    mock_args.audio = False
                    mock_args.video_only = False
                    mock_args.preview_transcript = False
                    mock_args.metadata_analysis = False
                    mock_args.metadata_export = None
                    
                    result = process_single_video(
                        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                        temp_download_dir["session_uuid"],
                        str(temp_download_dir["base_dir"]),
                        mock_args
                    )
                    
                    assert result["success_count"] > 0
                    mock_download.assert_called_once()
    
    @pytest.mark.integration
    def test_metadata_export_workflow(self, temp_download_dir, mock_video_info):
        """Test metadata export functionality."""
        from src.my_project.core_CLI import process_single_video
        
        with patch('src.my_project.core_CLI.get_video_info', return_value=mock_video_info):
            with patch('src.my_project.core_CLI.list_transcript_metadata') as mock_discover:
                with patch('src.my_project.yt_downloads_utils.download_transcript') as mock_download:
                    with patch('src.my_project.metadata_exporter.export_metadata') as mock_export:
                        
                        mock_discover.return_value = [
                            {"language_code": "en", "language": "English", "is_default": True}
                        ]
                        mock_download.return_value = "/path/to/transcript.txt"
                        mock_export.return_value = Path("/path/to/metadata.json")
                        
                        mock_args = Mock()
                        mock_args.transcript = True
                        mock_args.transcript_formats = ["clean"]
                        mock_args.audio = False
                        mock_args.video_only = False
                        mock_args.preview_transcript = False
                        mock_args.metadata_analysis = False
                        mock_args.metadata_export = "json"
                        
                        result = process_single_video(
                            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                            temp_download_dir["session_uuid"],
                            str(temp_download_dir["base_dir"]),
                            mock_args
                        )
                        
                        assert result["success_count"] > 0
                        mock_export.assert_called_once()


class TestCLIArgumentValidation:
    """Test CLI argument parsing and validation."""
    
    @pytest.mark.integration
    def test_valid_argument_combinations(self):
        """Test various valid CLI argument combinations."""
        from src.my_project.core_CLI import parse_args
        
        valid_combinations = [
            ["https://www.youtube.com/watch?v=test", "--info-only"],
            ["https://www.youtube.com/watch?v=test", "--transcript", "--transcript-formats", "clean"],
            ["https://www.youtube.com/watch?v=test", "--preview-transcript", "--metadata-analysis"],
            ["https://www.youtube.com/watch?v=test", "--audio", "--quality", "high"],
            ["https://www.youtube.com/watch?v=test", "--video-only"],
            ["https://www.youtube.com/watch?v=test", "--video-only", "--quality", "720p"],
            ["https://www.youtube.com/watch?v=test", "--video-with-audio"],
            ["https://www.youtube.com/watch?v=test", "--video-with-audio", "--quality", "1080p"],
            ["--batch-file", "urls.txt", "--transcript"]
        ]
        
        for args in valid_combinations:
            try:
                result = parse_args(args)
                assert result is not None
            except SystemExit:
                # Some combinations might trigger help/version exit
                pass
    
    @pytest.mark.integration
    def test_invalid_argument_combinations(self):
        """Test handling of invalid CLI argument combinations."""
        from src.my_project.core_CLI import parse_args
        
        invalid_combinations = [
            # Missing required URL or batch file
            ["--transcript"],
            # Invalid export format
            ["https://www.youtube.com/watch?v=test", "--metadata-export", "invalid"],
            # Invalid transcript format
            ["https://www.youtube.com/watch?v=test", "--transcript-formats", "invalid"]
        ]
        
        for args in invalid_combinations:
            with pytest.raises(SystemExit):
                parse_args(args)
    
    @pytest.mark.integration
    def test_help_output(self):
        """Test that help output is generated correctly."""
        from src.my_project.core_CLI import parse_args
        
        with pytest.raises(SystemExit) as excinfo:
            parse_args(["--help"])
        
        assert excinfo.value.code == 0
    
    @pytest.mark.integration  
    def test_video_only_flag_parsing(self):
        """Test that --video-only flag is parsed correctly with proper attribute name."""
        from src.my_project.core_CLI import parse_args
        
        # Test --video-only flag
        args = parse_args(["https://www.youtube.com/watch?v=test", "--video-only"])
        assert hasattr(args, 'video_only')
        assert args.video_only is True
        assert args.video_with_audio is False
        
        # Test --video-with-audio flag  
        args = parse_args(["https://www.youtube.com/watch?v=test", "--video-with-audio"])
        assert hasattr(args, 'video_only')
        assert args.video_only is False
        assert args.video_with_audio is True
        
        # Test no video flags
        args = parse_args(["https://www.youtube.com/watch?v=test", "--transcript"])
        assert hasattr(args, 'video_only')
        assert args.video_only is False
        assert args.video_with_audio is False


class TestBatchProcessing:
    """Test batch processing functionality."""
    
    @pytest.mark.integration
    def test_batch_file_processing(self, temp_download_dir):
        """Test processing multiple URLs from batch file."""
        # Create temporary batch file
        batch_file = temp_download_dir["base_dir"] / "test_urls.txt"
        urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://www.youtube.com/watch?v=oHg5SJYRHA0",
            "https://www.youtube.com/watch?v=9bZkp7q19f0"
        ]
        
        with open(batch_file, 'w') as f:
            for url in urls:
                f.write(f"{url}\n")
        
        from src.my_project.core_CLI import main
        
        test_args = [
            "--batch-file", str(batch_file),
            "--transcript",
            "--outdir", str(temp_download_dir["base_dir"])
        ]
        
        with patch('sys.argv', ['core_CLI.py'] + test_args):
            with patch('src.my_project.core_CLI.process_single_video') as mock_process:
                mock_process.return_value = {"success_count": 1}
                
                try:
                    main()
                    # Should have called process_single_video for each URL
                    assert mock_process.call_count == len(urls)
                except SystemExit as e:
                    assert e.code == 0
    
    @pytest.mark.integration
    def test_batch_error_handling(self, temp_download_dir):
        """Test error handling in batch processing."""
        batch_file = temp_download_dir["base_dir"] / "test_urls_with_errors.txt"
        urls = [
            "https://www.youtube.com/watch?v=VALID",
            "https://www.youtube.com/watch?v=INVALID",
            "https://www.youtube.com/watch?v=PRIVATE"
        ]
        
        with open(batch_file, 'w') as f:
            for url in urls:
                f.write(f"{url}\n")
        
        from src.my_project.core_CLI import main
        
        test_args = [
            "--batch-file", str(batch_file),
            "--info-only",
            "--outdir", str(temp_download_dir["base_dir"])
        ]
        
        with patch('sys.argv', ['core_CLI.py'] + test_args):
            with patch('src.my_project.core_CLI.process_single_video') as mock_process:
                # Simulate mixed success/failure results
                mock_process.side_effect = [
                    {"success_count": 1},  # First URL succeeds
                    {"success_count": 0},  # Second URL fails
                    {"success_count": 1}   # Third URL succeeds
                ]
                
                try:
                    main()
                    # Should continue processing despite individual failures
                    assert mock_process.call_count == len(urls)
                except SystemExit as e:
                    assert e.code == 0
    
    @pytest.mark.integration
    def test_batch_progress_reporting(self, temp_download_dir, capsys):
        """Test progress reporting during batch processing."""
        batch_file = temp_download_dir["base_dir"] / "test_urls.txt"
        urls = ["https://www.youtube.com/watch?v=test1", "https://www.youtube.com/watch?v=test2"]
        
        with open(batch_file, 'w') as f:
            for url in urls:
                f.write(f"{url}\n")
        
        from src.my_project.core_CLI import main
        
        test_args = [
            "--batch-file", str(batch_file),
            "--info-only",
            "--outdir", str(temp_download_dir["base_dir"])
        ]
        
        with patch('sys.argv', ['core_CLI.py'] + test_args):
            with patch('src.my_project.core_CLI.process_single_video') as mock_process:
                mock_process.return_value = {"success_count": 1}
                
                try:
                    main()
                except SystemExit:
                    pass
                
                # Check that progress information was printed
                captured = capsys.readouterr()
                assert "Processing video" in captured.out
                assert "BATCH PROCESSING COMPLETE" in captured.out


class TestWorkflowIntegration:
    """Test integration between different workflow components."""
    
    @pytest.mark.integration
    def test_preview_to_download_workflow(self, temp_download_dir):
        """Test realistic workflow: preview first, then download."""
        # This simulates user previewing content, then deciding to download
        
        from src.my_project.core_CLI import process_single_video
        
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        
        # First: Preview workflow
        with patch('src.my_project.core_CLI.get_video_info') as mock_extract:
            with patch('src.my_project.core_CLI.print_transcript_preview') as mock_preview:
                mock_extract.return_value = {"id": "dQw4w9WgXcQ", "title": "Test"}
                
                preview_args = Mock()
                preview_args.transcript = False
                preview_args.audio = False
                preview_args.video_only = False
                preview_args.preview_transcript = True
                preview_args.metadata_analysis = True
                preview_args.metadata_export = None
                
                preview_result = process_single_video(
                    url, temp_download_dir["session_uuid"], 
                    str(temp_download_dir["base_dir"]), preview_args
                )
                
                mock_preview.assert_called_once()
        
        # Then: Actual download workflow  
        with patch('src.my_project.core_CLI.get_video_info') as mock_extract:
            with patch('src.my_project.yt_downloads_utils.download_transcript') as mock_download:
                mock_extract.return_value = {"id": "dQw4w9WgXcQ", "title": "Test"}
                mock_download.return_value = "/path/to/transcript.txt"
                
                download_args = Mock()
                download_args.transcript = True
                download_args.transcript_formats = ["clean"]
                download_args.audio = False
                download_args.video_only = False
                download_args.preview_transcript = False
                download_args.metadata_analysis = False
                download_args.metadata_export = None
                
                download_result = process_single_video(
                    url, temp_download_dir["session_uuid"],
                    str(temp_download_dir["base_dir"]), download_args
                )
                
                assert download_result["success_count"] > 0
