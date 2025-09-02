#!/usr/bin/env python3
"""
test_metadata_exporter.py

Unit tests for metadata_exporter module.
Tests JSON, CSV, and Markdown export functionality.
"""

import pytest
import json
import csv
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
import tempfile
import os

from src.my_project.metadata_exporter import MetadataExporter, export_metadata


class TestMetadataExporter:
    """Test MetadataExporter class functionality."""
    
    def setup_method(self):
        """Set up test fixtures for each test method."""
        self.exporter = MetadataExporter()
        self.sample_metadata = {
            'collection_info': {
                'collected_at': '2024-01-01T12:00:00',
                'collector_version': '1.0',
                'analysis_enabled': True
            },
            'video_metadata': {
                'basic_info': {
                    'video_id': 'test123',
                    'title': 'Test Video',
                    'uploader': 'Test Channel',
                    'duration_seconds': 300,
                    'view_count': 1000
                },
                'engagement_metrics': {
                    'like_count': 50,
                    'engagement_rate_percent': 5.0
                }
            },
            'transcript_analysis': {
                'content_metrics': {
                    'word_count': 500,
                    'speaking_rate_wpm': 150
                },
                'quality_assessment': {
                    'quality_score': 85.5,
                    'quality_category': 'Very Good'
                }
            },
            'content_summary': {
                'overview': {
                    'title': 'Test Video',
                    'duration': '5m 0s'
                },
                'llm_suitability': {
                    'overall_score': 82.3,
                    'recommended_for_llm': True
                }
            }
        }
    
    def test_metadata_exporter_initialization(self):
        """Test MetadataExporter initialization."""
        exporter = MetadataExporter()
        assert exporter is not None
    
    @pytest.mark.unit
    def test_export_json_success(self, tmp_path):
        """Test successful JSON export."""
        output_file = tmp_path / "test_metadata.json"
        
        result = self.exporter.export_json(self.sample_metadata, str(output_file))
        
        assert result is True
        assert output_file.exists()
        
        # Verify content
        with open(output_file, 'r', encoding='utf-8') as f:
            exported_data = json.load(f)
        
        assert exported_data == self.sample_metadata
        assert exported_data['video_metadata']['basic_info']['video_id'] == 'test123'
    
    @pytest.mark.unit
    def test_export_json_directory_creation(self, tmp_path):
        """Test JSON export creates directories if they don't exist."""
        nested_dir = tmp_path / "subdir" / "nested"
        output_file = nested_dir / "test_metadata.json"
        
        result = self.exporter.export_json(self.sample_metadata, str(output_file))
        
        assert result is True
        assert output_file.exists()
        assert nested_dir.exists()
    
    @pytest.mark.unit
    def test_export_json_file_error(self, tmp_path):
        """Test JSON export handles file write errors."""
        # Try to write to a read-only directory
        readonly_dir = tmp_path / "readonly"
        readonly_dir.mkdir()
        readonly_dir.chmod(0o444)  # Read-only
        
        output_file = readonly_dir / "test_metadata.json"
        
        result = self.exporter.export_json(self.sample_metadata, str(output_file))
        
        assert result is False
    
    @pytest.mark.unit
    def test_export_csv_success(self, tmp_path):
        """Test successful CSV export."""
        output_file = tmp_path / "test_metadata.csv"
        
        result = self.exporter.export_csv(self.sample_metadata, str(output_file))
        
        assert result is True
        assert output_file.exists()
        
        # Verify CSV structure
        with open(output_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            
        assert len(rows) >= 1
        # Check some expected flattened fields exist
        assert any('video_id' in row for row in rows)
    
    @pytest.mark.unit
    def test_export_csv_empty_metadata(self, tmp_path):
        """Test CSV export with empty metadata."""
        output_file = tmp_path / "empty_metadata.csv"
        empty_metadata = {}
        
        result = self.exporter.export_csv(empty_metadata, str(output_file))
        
        assert result is False  # Should fail with empty data
    
    @pytest.mark.unit
    def test_export_markdown_success(self, tmp_path):
        """Test successful Markdown export."""
        output_file = tmp_path / "test_metadata.md"
        
        result = self.exporter.export_markdown(self.sample_metadata, str(output_file))
        
        assert result is True
        assert output_file.exists()
        
        # Verify markdown content
        with open(output_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert '# Video Metadata Report' in content
        assert 'Test Video' in content
        assert 'Test Channel' in content
        assert '## Video Information' in content
    
    @pytest.mark.unit
    def test_export_markdown_with_transcript_analysis(self, tmp_path):
        """Test Markdown export includes transcript analysis sections."""
        output_file = tmp_path / "test_metadata_with_transcript.md"
        
        result = self.exporter.export_markdown(self.sample_metadata, str(output_file))
        
        assert result is True
        
        with open(output_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert '## Content Analysis' in content
        assert '500' in content  # word count
        assert '150' in content  # speaking rate
        assert '## Quality Assessment' in content
        assert 'Very Good' in content
    
    @pytest.mark.unit
    def test_flatten_metadata_for_csv(self):
        """Test metadata flattening for CSV export."""
        flattened = self.exporter._flatten_metadata_for_csv(self.sample_metadata)
        
        assert isinstance(flattened, dict)
        assert 'video_id' in flattened
        assert 'title' in flattened
        assert 'word_count' in flattened
        assert 'quality_score' in flattened
        
        # Check values are preserved
        assert flattened['video_id'] == 'test123'
        assert flattened['title'] == 'Test Video'
        assert flattened['word_count'] == 500
        assert flattened['quality_score'] == 85.5
    
    @pytest.mark.unit
    def test_flatten_nested_dict(self):
        """Test flattening deeply nested dictionaries."""
        nested_data = {
            'level1': {
                'level2': {
                    'level3': {
                        'value': 'deep_value'
                    }
                }
            }
        }
        
        flattened = self.exporter._flatten_dict(nested_data)
        
        assert 'level1_level2_level3_value' in flattened
        assert flattened['level1_level2_level3_value'] == 'deep_value'
    
    @pytest.mark.unit  
    def test_add_video_info_section(self):
        """Test adding video information section to markdown."""
        sections = []
        
        self.exporter._add_video_info_section(sections, self.sample_metadata['video_metadata'])
        
        assert len(sections) > 0
        content = '\n'.join(sections)
        assert '## Video Information' in content
        assert 'Test Video' in content
        assert 'Test Channel' in content
        assert '300 seconds' in content or '5m 0s' in content
    
    @pytest.mark.unit
    def test_add_content_analysis_section(self):
        """Test adding content analysis section to markdown."""
        sections = []
        
        self.exporter._add_content_analysis_section(sections, self.sample_metadata['transcript_analysis'])
        
        assert len(sections) > 0
        content = '\n'.join(sections)
        assert '## Content Analysis' in content
        assert '500' in content  # word count
        assert '150' in content  # speaking rate
    
    @pytest.mark.unit
    def test_add_llm_suitability_section(self):
        """Test adding LLM suitability section to markdown."""
        sections = []
        
        self.exporter._add_llm_suitability_section(sections, self.sample_metadata['content_summary'])
        
        assert len(sections) > 0
        content = '\n'.join(sections)
        assert '## LLM Analysis Suitability' in content
        assert '82.3' in content  # overall score
        assert 'Recommended' in content


class TestExportMetadataFunction:
    """Test the standalone export_metadata function."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.sample_metadata = {
            'video_metadata': {'basic_info': {'title': 'Test'}},
            'collection_info': {'collected_at': '2024-01-01T12:00:00'}
        }
    
    @pytest.mark.unit
    def test_export_metadata_json(self, tmp_path):
        """Test export_metadata function with JSON format."""
        output_file = tmp_path / "test.json"
        
        result = export_metadata(self.sample_metadata, 'json', str(output_file))
        
        assert result is True
        assert output_file.exists()
    
    @pytest.mark.unit
    def test_export_metadata_csv(self, tmp_path):
        """Test export_metadata function with CSV format."""
        output_file = tmp_path / "test.csv"
        
        result = export_metadata(self.sample_metadata, 'csv', str(output_file))
        
        assert result is True
        assert output_file.exists()
    
    @pytest.mark.unit
    def test_export_metadata_markdown(self, tmp_path):
        """Test export_metadata function with Markdown format."""
        output_file = tmp_path / "test.md"
        
        result = export_metadata(self.sample_metadata, 'markdown', str(output_file))
        
        assert result is True
        assert output_file.exists()
    
    @pytest.mark.unit
    def test_export_metadata_unsupported_format(self, tmp_path):
        """Test export_metadata function with unsupported format."""
        output_file = tmp_path / "test.xml"
        
        result = export_metadata(self.sample_metadata, 'xml', str(output_file))
        
        assert result is False
    
    @pytest.mark.unit
    def test_export_metadata_case_insensitive(self, tmp_path):
        """Test export_metadata function handles case-insensitive formats."""
        output_file = tmp_path / "test.json"
        
        # Test uppercase format
        result = export_metadata(self.sample_metadata, 'JSON', str(output_file))
        assert result is True
        
        # Test mixed case format
        output_file2 = tmp_path / "test2.csv"
        result = export_metadata(self.sample_metadata, 'Csv', str(output_file2))
        assert result is True


class TestMetadataExporterEdgeCases:
    """Test edge cases and error conditions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.exporter = MetadataExporter()
    
    @pytest.mark.unit
    def test_export_with_none_metadata(self, tmp_path):
        """Test export functions handle None metadata gracefully."""
        output_file = tmp_path / "test.json"
        
        result = self.exporter.export_json(None, str(output_file))
        assert result is False
    
    @pytest.mark.unit
    def test_export_with_empty_string_path(self):
        """Test export functions handle empty path strings."""
        result = self.exporter.export_json({'test': 'data'}, '')
        assert result is False
    
    @pytest.mark.unit
    def test_export_with_invalid_json_data(self, tmp_path):
        """Test JSON export with non-serializable data."""
        output_file = tmp_path / "test.json"
        
        # Create data with non-serializable object
        invalid_data = {
            'function': lambda x: x,  # Functions can't be JSON serialized
            'valid_data': 'test'
        }
        
        # Should handle this gracefully due to default=str in json.dump
        result = self.exporter.export_json(invalid_data, str(output_file))
        assert result is True  # Should succeed with default=str handling
    
    @pytest.mark.unit
    def test_markdown_export_missing_sections(self, tmp_path):
        """Test Markdown export with missing metadata sections."""
        output_file = tmp_path / "minimal.md"
        minimal_metadata = {
            'collection_info': {'collected_at': '2024-01-01T12:00:00'}
        }
        
        result = self.exporter.export_markdown(minimal_metadata, str(output_file))
        
        assert result is True
        assert output_file.exists()
        
        # Should still create a valid markdown file
        with open(output_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert '# Video Metadata Report' in content
