"""
Tests for the main module.
"""

import pytest
from sunny_osprey.main import run_mqtt_processor, parse_arguments


class TestParseArguments:
    """Test cases for the parse_arguments function."""
    
    def test_parse_arguments_defaults(self):
        """Test parse_arguments with default values."""
        # Mock sys.argv to avoid actual command line parsing
        import sys
        original_argv = sys.argv
        sys.argv = ['test_main.py']
        
        try:
            args = parse_arguments()
            assert args.mqtt_host == 'mqtt'  # Default from env or 'mqtt'
            assert args.mqtt_port == 1883
            assert args.api_base_url == 'http://frigate:5000'
            assert args.prompt_file == '/app/prompt.txt'
        finally:
            sys.argv = original_argv
    
    def test_parse_arguments_custom_values(self):
        """Test parse_arguments with custom values."""
        import sys
        original_argv = sys.argv
        sys.argv = [
            'test_main.py',
            '--mqtt-host', 'localhost',
            '--mqtt-port', '1884',
            '--api-base-url', 'http://localhost:5001',
            '--prompt-file', '/custom/prompt.txt'
        ]
        
        try:
            args = parse_arguments()
            assert args.mqtt_host == 'localhost'
            assert args.mqtt_port == 1884
            assert args.api_base_url == 'http://localhost:5001'
            assert args.prompt_file == '/custom/prompt.txt'
        finally:
            sys.argv = original_argv


class TestRunMqttProcessor:
    """Test cases for the run_mqtt_processor function."""
    
    def test_run_mqtt_processor_initialization(self):
        """Test that run_mqtt_processor can be called without errors."""
        # Mock the FrigateEventProcessor and LLMInferenceEngine to avoid actual connections
        from unittest.mock import patch, Mock
        
        with patch('sunny_osprey.llm_inference.LLMInferenceEngine') as mock_llm_class, \
             patch('sunny_osprey.mqtt_processor.FrigateEventProcessor') as mock_processor_class:
            
            # Mock the LLM engine instance
            mock_llm_engine = Mock()
            mock_llm_class.return_value = mock_llm_engine
            
            # Mock the processor instance and its start method to raise KeyboardInterrupt to break the while loop
            mock_processor = Mock()
            mock_processor.start = Mock(side_effect=KeyboardInterrupt("Test interrupt to break loop"))
            mock_processor.stop = Mock()
            mock_processor_class.return_value = mock_processor
            
            # Call the function with test parameters
            run_mqtt_processor(
                mqtt_host="test",
                mqtt_port=1883,
                api_base_url="http://test:5000",
                prompt_file="/app/prompt.txt"
            )
            
            # Verify that LLMInferenceEngine was called
            mock_llm_class.assert_called_once_with(prompt_file="/app/prompt.txt")
            mock_llm_engine._initialize_model.assert_called_once()
            
            # Verify that FrigateEventProcessor was called with correct parameters
            mock_processor_class.assert_called_once_with(
                mqtt_host="test",
                mqtt_port=1883,
                api_base_url="http://test:5000",
                prompt_file="/app/prompt.txt",
                llm_engine=mock_llm_engine
            )
            
            # Verify that the processor's start method was called
            mock_processor.start.assert_called_once()
