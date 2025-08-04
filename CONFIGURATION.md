# Sunny Osprey Configuration

Sunny Osprey uses a YAML configuration file to control its behavior. The configuration file is located at `/app/sunny-osprey-config.yaml` by default.

## Configuration File Structure

### MQTT Configuration
```yaml
mqtt:
  enabled: true
  host: mqtt
  port: 1883
  topic: frigate/events
```

### Frigate API Configuration
```yaml
frigate:
  api_base_url: http://frigate:5000
```

### Camera Filtering
The most important feature is camera filtering, which allows you to specify which cameras to process:

```yaml
cameras:
  enabled_cameras:
    - LPR
    - FRONT_DOOR
    # - BACKYARD  # Commented out cameras are ignored
    # - GARAGE
```

**Important**: If no cameras are specified (empty list), Sunny Osprey will process events from ALL cameras.

### LLM Configuration
```yaml
llm:
  prompt_file: /app/prompt.txt
  model_name: gemma-3n-E2B-it
  max_new_tokens: 500
  max_memory:
    0: "10GB"  # GPU memory limit
    cpu: "4GB"  # CPU memory limit for fallback
```

### Alert Configuration
```yaml
alerts:
  # Global alert settings
  send_all_activities: false  # Set to true to send all activities, false for suspicious only
  
  telegram:
    bot_token: ${TELEGRAM_BOT_TOKEN}
    chat_id: ${TELEGRAM_CHAT_ID}
  
  # Grafana IRM (Incident Response Management) alerts
  grafana:
    url: ${GRAFANA_URL}
    api_key: ${GRAFANA_API_KEY}
```

### Logging Configuration
```yaml
logging:
  level: INFO
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

## Environment Variables

The configuration supports environment variable substitution using `${VARIABLE_NAME}` syntax. You can also use a `.env` file for sensitive configuration.

### Supported Environment Variables

- `MQTT_HOST`: MQTT broker host (default: mqtt)
- `MQTT_PORT`: MQTT broker port (default: 1883)
- `FRIGATE_API_URL`: Frigate API base URL (default: http://frigate:5000)
- `TELEGRAM_BOT_TOKEN`: Your Telegram bot token
- `TELEGRAM_CHAT_ID`: Your Telegram chat ID
- `GRAFANA_URL`: Grafana IRM URL
- `GRAFANA_API_KEY`: Grafana IRM API key
- `HF_TOKEN`: Hugging Face token for model downloads

### Using .env File

Create a `.env` file in the same directory as your config file or in the `/app` directory:

```bash
# .env file example
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_telegram_chat_id_here
GRAFANA_URL=your_grafana_url_here
GRAFANA_API_KEY=your_grafana_api_key_here
```

The system will automatically load the `.env` file if it exists.

## Usage Examples

### Alert Configuration Examples

#### Send Only Suspicious Activities (Default)
```yaml
alerts:
  send_all_activities: false
  telegram:
    bot_token: ${TELEGRAM_BOT_TOKEN}
    chat_id: ${TELEGRAM_CHAT_ID}
```

#### Send All Activities
```yaml
alerts:
  send_all_activities: true
  telegram:
    bot_token: ${TELEGRAM_BOT_TOKEN}
    chat_id: ${TELEGRAM_CHAT_ID}
```

### Process Only LPR Camera
```yaml
cameras:
  enabled_cameras:
    - LPR
```

### Process Multiple Specific Cameras
```yaml
cameras:
  enabled_cameras:
    - LPR
    - FRONT_DOOR
    - BACKYARD
```

### Process All Cameras (Default)
```yaml
cameras:
  enabled_cameras: []
```

## Command Line Override

You can specify a different configuration file using the `--config` argument:

```bash
python src/sunny_osprey/main.py --config /path/to/custom-config.yaml
```

## Docker Usage

When running with Docker, the configuration file is mounted from the host:

```yaml
volumes:
  - ./sunny-osprey-config.yaml:/app/sunny-osprey-config.yaml:ro
```

## Camera Names

Camera names in the configuration must match exactly the camera names in your Frigate events. You can find the camera names in the Frigate events JSON, for example:

```json
{
  "camera": "LPR",
  "label": "person",
  "score": 0.8
}
```

In this example, the camera name is `"LPR"`. 