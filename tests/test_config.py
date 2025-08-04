"""
Tests for the Sunny Osprey configuration module.
"""

import pytest
import tempfile
import os
import yaml
from sunny_osprey.config import SunnyOspreyConfig


class TestSunnyOspreyConfig:
    """Test cases for SunnyOspreyConfig class."""
    
    def test_default_config(self):
        """Test that default configuration is loaded when no file exists."""
        config = SunnyOspreyConfig("/nonexistent/path.yaml")
        
        # Check that default values are set
        assert config.get_mqtt_host() == "mqtt"
        assert config.get_mqtt_port() == 1883
        assert config.get_frigate_api_url() == "http://frigate:5000"
        assert config.get_prompt_file() == "/app/prompt.txt"
    
    def test_load_config_from_file(self):
        """Test loading configuration from a YAML file."""
        config_data = {
            'mqtt': {
                'host': 'test-mqtt',
                'port': 1884
            },
            'frigate': {
                'api_base_url': 'http://test-frigate:5001'
            },
            'cameras': {
                'enabled_cameras': ['LPR', 'FRONT_DOOR']
            },
            'llm': {
                'prompt_file': '/test/prompt.txt'
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name
        
        try:
            config = SunnyOspreyConfig(config_path)
            
            assert config.get_mqtt_host() == "test-mqtt"
            assert config.get_mqtt_port() == 1884
            assert config.get_frigate_api_url() == "http://test-frigate:5001"
            assert config.get_prompt_file() == "/test/prompt.txt"
            
            # Test camera filtering
            assert config.should_process_camera("LPR") == True
            assert config.should_process_camera("FRONT_DOOR") == True
            assert config.should_process_camera("BACKYARD") == False
            
        finally:
            os.unlink(config_path)
    
    def test_camera_filtering(self):
        """Test camera filtering functionality."""
        config_data = {
            'cameras': {
                'enabled_cameras': ['LPR', 'FRONT_DOOR']
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name
        
        try:
            config = SunnyOspreyConfig(config_path)
            
            # Test specific cameras
            assert config.should_process_camera("LPR") == True
            assert config.should_process_camera("FRONT_DOOR") == True
            assert config.should_process_camera("BACKYARD") == False
            assert config.should_process_camera("GARAGE") == False
            
        finally:
            os.unlink(config_path)
    
    def test_all_cameras_when_none_specified(self):
        """Test that all cameras are processed when none are specified."""
        config_data = {
            'cameras': {
                'enabled_cameras': []
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name
        
        try:
            config = SunnyOspreyConfig(config_path)
            
            # All cameras should be processed
            assert config.should_process_camera("LPR") == True
            assert config.should_process_camera("FRONT_DOOR") == True
            assert config.should_process_camera("BACKYARD") == True
            assert config.should_process_camera("ANY_CAMERA") == True
            
        finally:
            os.unlink(config_path)
    
    def test_event_filtering(self):
        """Test event filtering based on configuration."""
        config_data = {
            'cameras': {
                'enabled_cameras': ['LPR']
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name
        
        try:
            config = SunnyOspreyConfig(config_path)
            
            # Test event that should be processed
            good_event = {
                'camera': 'LPR',
                'label': 'person',
                'score': 0.8
            }
            assert config.should_skip_event(good_event) == False
            
            # Test event from wrong camera
            wrong_camera_event = {
                'camera': 'BACKYARD',
                'label': 'person',
                'score': 0.8
            }
            assert config.should_skip_event(wrong_camera_event) == True
            
        finally:
            os.unlink(config_path) 