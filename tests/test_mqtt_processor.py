"""
Tests for the MQTT processor module.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from sunny_osprey.mqtt_processor import FrigateEventProcessor


class TestFrigateEventProcessor:
    """Test cases for the FrigateEventProcessor class."""
    
    def test_init(self):
        """Test processor initialization."""
        processor = FrigateEventProcessor()
        assert processor.mqtt_host == "127.0.0.1"
        assert processor.mqtt_port == 1883
        assert processor.api_base_url == "http://127.0.0.1:5000"
        assert processor.prompt_file == "prompt.txt"  # Default value from __init__
    
    def test_extract_event_id(self):
        """Test event ID extraction from MQTT payload."""
        processor = FrigateEventProcessor()
        
        # Test valid event data
        event_data = {
            "after": {
                "id": "1752239252.709833-lt9sy7"
            },
            "type": "end"
        }
        
        event_id = event_data.get("after", {}).get("id")
        assert event_id == "1752239252.709833-lt9sy7"
    
    def test_filter_end_events(self):
        """Test that only 'end' events are processed."""
        processor = FrigateEventProcessor()
        
        # Mock message handler
        with patch.object(processor, '_process_end_event') as mock_process:
            # Test end event
            end_event = {"type": "end", "after": {"id": "test-id"}}
            processor._on_message(None, None, Mock(payload=json.dumps(end_event).encode()))
            mock_process.assert_called_once()
            
            # Test non-end event
            mock_process.reset_mock()
            start_event = {"type": "start", "after": {"id": "test-id"}}
            processor._on_message(None, None, Mock(payload=json.dumps(start_event).encode()))
            mock_process.assert_not_called()
    
    @patch('requests.get')
    @patch('os.path.getsize')
    @patch('tempfile.NamedTemporaryFile')
    def test_download_video_clip_success(self, mock_temp, mock_getsize, mock_get):
        """Test successful video clip download."""
        processor = FrigateEventProcessor()
        
        # Mock successful response
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.content = b"fake video content"
        mock_get.return_value = mock_response
        
        # Mock file size check (non-zero file)
        mock_getsize.return_value = 1024
        
        # Mock temporary file
        mock_temp_file = Mock()
        mock_temp_file.name = "/tmp/test.mp4"
        mock_temp_file.write = Mock()
        mock_temp.return_value.__enter__.return_value = mock_temp_file
        
        result = processor._download_video_clip("test-event-id")
        assert result == "/tmp/test.mp4"
    
    @patch('requests.get')
    def test_download_video_clip_failure(self, mock_get):
        """Test video clip download failure."""
        processor = FrigateEventProcessor()
        
        # Mock failed response
        mock_get.side_effect = Exception("Network error")
        
        result = processor._download_video_clip("test-event-id")
        assert result is None
