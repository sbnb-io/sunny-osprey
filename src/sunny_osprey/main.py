"""
Main module for the Sunny Osprey project.
"""

import argparse
import sys
import time
import os

def run_mqtt_processor(config_path: str = "/app/sunny-osprey-config.yaml"):
    """Run the MQTT event processor with retry logic for MQTT connection."""
    from sunny_osprey.mqtt_processor import FrigateEventProcessor
    from sunny_osprey.llm_inference import LLMInferenceEngine
    from sunny_osprey.config import SunnyOspreyConfig
    
    print("🚀 Initializing Sunny Osprey Security Camera Analysis System")
    print("=" * 60)
    
    # Load configuration
    print("📋 Loading configuration...")
    config = SunnyOspreyConfig(config_path)
    
    # Get configuration values
    mqtt_config = config.get_mqtt_config()
    frigate_config = config.get_frigate_config()
    llm_config = config.get_llm_config()
    
    mqtt_host = mqtt_config.get('host', 'mqtt')
    mqtt_port = mqtt_config.get('port', 1883)
    api_base_url = frigate_config.get('api_base_url', 'http://frigate:5000')
    prompt_file = llm_config.get('prompt_file', '/app/prompt.txt')
    
    # Initialize LLM model at startup
    print("🧠 Initializing LLM model...")
    try:
        llm_engine = LLMInferenceEngine(prompt_file=prompt_file, config=llm_config)
        # Force model initialization
        llm_engine._initialize_model()
        print("✅ LLM model initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize LLM model: {e}")
        print("Exiting due to LLM initialization failure")
        return 1
    
    processor = FrigateEventProcessor(
        mqtt_host=mqtt_host,
        mqtt_port=mqtt_port,
        api_base_url=api_base_url,
        prompt_file=prompt_file,
        llm_engine=llm_engine,  # Pass the initialized engine
        config=config  # Pass the configuration
    )
    
    print("📡 Initializing MQTT connection...")
    
    # Display camera filtering info
    enabled_cameras = config.get_camera_config().get('enabled_cameras', [])
    if enabled_cameras:
        print(f"📹 Processing events from cameras: {', '.join(enabled_cameras)}")
    else:
        print("📹 Processing events from all cameras")
    
    while True:
        try:
            print("Starting Frigate Event Processor...")
            print(f"Listening for MQTT events on frigate/events")
            print(f"MQTT Host: {mqtt_host}:{mqtt_port}")
            print(f"Frigate API: {api_base_url}")
            print(f"Prompt file: {prompt_file}")
            print("Press Ctrl+C to stop")
            processor.start()
        except KeyboardInterrupt:
            print("\nStopping...")
            processor.stop()
            break
        except Exception as e:
            print(f"Error: {e}")
            print("Retrying connection to MQTT broker in 5 seconds...")
        finally:
            # Only sleep if not exiting due to KeyboardInterrupt
            time.sleep(5)

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Sunny Osprey MQTT Event Processor")
    parser.add_argument("--config", default="/app/sunny-osprey-config.yaml",
                       help="Path to configuration file (default: /app/sunny-osprey-config.yaml)")
    
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_arguments()
    run_mqtt_processor(config_path=args.config)
