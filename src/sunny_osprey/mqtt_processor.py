"""
MQTT Event Processor for Frigate Security Camera Events
"""

import json
import logging
import os
import tempfile
import time
from typing import Dict, Any, Optional
import requests
import paho.mqtt.client as mqtt
from .llm_inference import LLMInferenceEngine
from .alert_manager import AlertManager, is_suspicious_activity_detected
from .config import SunnyOspreyConfig
import signal
import sys


class FrigateEventProcessor:
    """Processes Frigate MQTT events and runs LLM inference on video clips."""
    
    def __init__(self, mqtt_host: str = "127.0.0.1", mqtt_port: int = 1883,
                 api_base_url: str = "http://127.0.0.1:5000",
                 prompt_file: str = "prompt.txt", llm_engine: Optional[LLMInferenceEngine] = None,
                 config: Optional[SunnyOspreyConfig] = None):
        """
        Initialize the Frigate event processor.
        
        Args:
            mqtt_host: MQTT broker host
            mqtt_port: MQTT broker port
            api_base_url: Frigate API base URL
            prompt_file: Path to the prompt file for LLM inference
            llm_engine: Optional pre-initialized LLM inference engine
            config: Optional configuration object
        """
        # Load configuration
        self.config = config or SunnyOspreyConfig()
        
        # Use config values if not explicitly provided
        self.mqtt_host = mqtt_host or self.config.get_mqtt_host()
        self.mqtt_port = mqtt_port or self.config.get_mqtt_port()
        self.api_base_url = api_base_url or self.config.get_frigate_api_url()
        self.prompt_file = prompt_file or self.config.get_prompt_file()
        
        # Initialize MQTT client
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = self._on_connect
        self.mqtt_client.on_message = self._on_message
        
        # Use provided LLM engine or create new one
        if llm_engine is not None:
            self.llm_engine = llm_engine
        else:
            llm_config = self.config.get_llm_config()
            self.llm_engine = LLMInferenceEngine(prompt_file=prompt_file, config=llm_config)
        
        # Initialize Alert Manager
        alerts_config = self.config.get_alerts_config()
        self.alert_manager = AlertManager(alerts_config)
        
        # Setup logging is now handled by config
        self.logger = logging.getLogger(__name__)
    
    def _on_connect(self, client, userdata, flags, rc):
        """Callback for MQTT connection."""
        if rc == 0:
            self.logger.info("Connected to MQTT broker")
            client.subscribe("frigate/events")
            self.logger.info("Subscribed to frigate/events")
            # Indicate readiness for healthcheck
            try:
                with open("/shared/ready", "w") as f:
                    f.write("ready\n")
            except Exception as e:
                self.logger.warning(f"Failed to write readiness file: {e}")
        else:
            self.logger.error(f"Failed to connect to MQTT broker with code {rc}")
    
    def _on_message(self, client, userdata, msg):
        """Callback for MQTT messages."""
        try:
            payload = json.loads(msg.payload.decode())
            self.logger.info(f"Received MQTT event: {payload.get('type', 'unknown')}")
            
            # Process only "end" events
            if payload.get("type") == "end":
                # Check if we should process this event based on configuration
                if self._should_process_event(payload):
                    self._process_end_event(payload)
                else:
                    self.logger.debug(f"Skipping event based on configuration filters")
            else:
                self.logger.debug(f"Skipping non-end event: {payload.get('type')}")
                
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse MQTT message: {e}")
        except Exception as e:
            self.logger.error(f"Error processing MQTT message: {e}")
    
    def _should_process_event(self, event_data: Dict[str, Any]) -> bool:
        """
        Check if an event should be processed based on configuration filters.
        
        Args:
            event_data: Event data from Frigate
            
        Returns:
            True if event should be processed, False otherwise
        """
        try:
            # Extract camera name from event
            camera_name = None
            if 'after' in event_data and event_data['after']:
                camera_name = event_data['after'].get('camera')
            elif 'before' in event_data and event_data['before']:
                camera_name = event_data['before'].get('camera')
            
            if camera_name:
                self.logger.debug(f"Event from camera: {camera_name}")
                
                # Check camera filtering
                if not self.config.should_process_camera(camera_name):
                    self.logger.info(f"Skipping event from camera '{camera_name}' (not in enabled cameras list)")
                    return False
            
            # Check other filters using the config
            if self.config.should_skip_event(event_data.get('after', {}) or event_data.get('before', {})):
                self.logger.info(f"Skipping event based on processing filters")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking if event should be processed: {e}")
            # Default to processing if there's an error
            return True
    
    def _process_end_event(self, event_data: Dict[str, Any]):
        """Process an end event from Frigate."""
        try:
            # Extract event ID
            event_id = event_data.get("after", {}).get("id")
            if not event_id:
                self.logger.error("No event ID found in event data")
                return
            
            self.logger.info(f"Processing end event: {event_id}")
            
            # Download video clip
            video_path = self._download_video_clip(event_id, event_data)
            if not video_path:
                return
            
            # Run LLM inference
            result = self.llm_engine.run_inference(video_path)
            if result:
                # Add video_path to result for Telegram video sending
                result['video_path'] = video_path
                print(json.dumps(result, indent=2))
                
                # Send incident to alert manager for all events
                is_suspicious = is_suspicious_activity_detected(result)
                if is_suspicious:
                    self.logger.info(f"Suspicious activity detected for event {event_id}, processing alert")
                else:
                    self.logger.info(f"Normal activity detected for event {event_id}, processing notification")
                
                incident_sent = self.alert_manager.send_incident(event_id, result)
                if incident_sent:
                    self.logger.info(f"Alert/notification processed successfully for event {event_id}")
                else:
                    self.logger.warning(f"Failed to process alert/notification for event {event_id}")
            
            # Clean up temporary file (but not local test files)
            if not video_path.startswith('/app/test_videos/'):
                try:
                    os.remove(video_path)
                    self.logger.debug(f"Cleaned up temporary file: {video_path}")
                except Exception as e:
                    self.logger.warning(f"Failed to clean up {video_path}: {e}")
            else:
                self.logger.debug(f"Keeping local test file: {video_path}")
                
        except Exception as e:
            self.logger.error(f"Error processing end event: {e}")
    
    def _download_video_clip(self, event_id: str, event_data: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """Download video clip from Frigate API or use local test file."""
        try:
            # Check if this is a test event with local video path
            if event_id.startswith('test_'):
                # Extract video path from event data
                if event_data and 'after' in event_data:
                    video_path = event_data['after'].get('video_path')
                    if video_path and os.path.exists(video_path):
                        self.logger.info(f"Using local test video: {video_path}")
                        return video_path
                    else:
                        self.logger.error(f"Test video file not found: {video_path}")
                        return None
                else:
                    self.logger.error(f"No event data provided for test event: {event_id}")
                    return None
            
            # Regular Frigate API download
            url = f"{self.api_base_url}/api/events/{event_id}/clip.mp4"
            self.logger.info(f"Downloading video clip from: {url}")
            
            for attempt in range(3):
                try:
                    response = requests.get(url, timeout=30)
                    response.raise_for_status()

                    # Save to temporary file
                    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
                        f.write(response.content)
                        temp_path = f.name
                    # Check file size
                    file_size = os.path.getsize(temp_path)
                    self.logger.info(f"Downloaded video clip to: {temp_path}, size: {file_size} bytes ({file_size / (1024*1024):.2f} MB)")

                    if file_size == 0:
                        self.logger.warning(f"Attempt {attempt+1}/3: Downloaded file is empty (0 bytes)")
                        os.remove(temp_path)  # Clean up empty file
                        if attempt == 2:  # Last attempt
                            self.logger.error("Failed to download non-empty video clip after 3 attempts")
                            return None
                        time.sleep(3)  # Wait before retry
                        continue
                    else:
                        return temp_path

                except Exception as e:
                    self.logger.error(f"Attempt {attempt+1}/3: Failed to download video clip: {e}")
                    if attempt == 2:  # Last attempt
                        return None
                    time.sleep(3)  # Wait before retry

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to download video clip: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error downloading video clip: {e}")
            return None
    

    
    def start(self):
        """Start the MQTT client and begin processing events."""
        try:
            self.logger.info(f"Connecting to MQTT broker at {self.mqtt_host}:{self.mqtt_port}")
            self.mqtt_client.connect(self.mqtt_host, self.mqtt_port, 60)
            self.mqtt_client.loop_forever()
        except Exception as e:
            self.logger.error(f"Failed to start MQTT client: {e}")
    
    def stop(self):
        """Stop the MQTT client."""
        self.mqtt_client.loop_stop()
        self.mqtt_client.disconnect()
        self.logger.info("MQTT client stopped")


def main():
    """Main entry point."""
    processor = FrigateEventProcessor()

    def handle_exit(signum, frame):
        print(f"Received signal {signum}, shutting down gracefully...")
        try:
            processor.stop()
        except Exception as e:
            print(f"Error during shutdown: {e}")
        sys.exit(0)

    # Register signal handlers
    signal.signal(signal.SIGTERM, handle_exit)
    signal.signal(signal.SIGINT, handle_exit)

    try:
        print("Starting Frigate Event Processor...")
        print("Listening for MQTT events on frigate/events")
        print("Press Ctrl+C to stop")
        processor.start()
    except KeyboardInterrupt:
        print("\nStopping...")
        processor.stop()


if __name__ == "__main__":
    main()
