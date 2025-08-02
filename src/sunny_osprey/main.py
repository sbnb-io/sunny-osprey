"""
Main module for the Sunny Osprey project.
"""

import argparse
import sys
import time
import os

def run_mqtt_processor(mqtt_host: str = None, mqtt_port: int = None,
                       api_base_url: str = None,
                       prompt_file: str = "/app/prompt.txt"):
    """Run the MQTT event processor with retry logic for MQTT connection."""
    from sunny_osprey.mqtt_processor import FrigateEventProcessor
    from sunny_osprey.llm_inference import LLMInferenceEngine
    
    print("🚀 Initializing Sunny Osprey Security Camera Analysis System")
    print("=" * 60)
    
    # Initialize LLM model at startup
    print("🧠 Initializing LLM model...")
    try:
        llm_engine = LLMInferenceEngine(prompt_file=prompt_file)
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
        llm_engine=llm_engine  # Pass the initialized engine
    )
    
    print("📡 Initializing MQTT connection...")
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
    parser.add_argument("--mqtt-host", default=os.getenv('MQTT_HOST', 'mqtt'), 
                       help="MQTT broker host (default: MQTT_HOST env var or mqtt)")
    parser.add_argument("--mqtt-port", type=int, default=int(os.getenv('MQTT_PORT', '1883')),
                       help="MQTT broker port (default: MQTT_PORT env var or 1883)")
    parser.add_argument("--api-base-url", default=os.getenv('FRIGATE_API_URL', 'http://frigate:5000'),
                       help="Frigate API base URL (default: FRIGATE_API_URL env var or http://frigate:5000)")
    parser.add_argument("--prompt-file", default="/app/prompt.txt",
                       help="Path to prompt file (default: /app/prompt.txt)")
    
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_arguments()
    run_mqtt_processor(
        mqtt_host=args.mqtt_host,
        mqtt_port=args.mqtt_port,
        api_base_url=args.api_base_url,
        prompt_file=args.prompt_file
    )
