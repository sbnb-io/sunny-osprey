#!/bin/bash

# Inject Test Events for Sunny Osprey
# This script injects fake MQTT events to trigger analysis of local test files

echo "Injecting test events for Sunny Osprey..."

# Test event IDs
CRIMINAL_EVENT_ID="test_criminal_$(date +%s)"
GATE_EVENT_ID="test_gate_$(date +%s)"

echo "Test event IDs:"
echo "  Criminal: $CRIMINAL_EVENT_ID"
echo "  Gate: $GATE_EVENT_ID"

# Function to inject a test event
inject_test_event() {
    local event_id=$1
    local video_file=$2
    local description=$3
    
    echo "Injecting test event: $event_id ($description)"
    
    # Create fake MQTT event payload
    payload=$(cat << 'EOF'
{
  "type": "end",
  "after": {
    "id": "$event_id",
    "video_path": "/app/test_videos/$video_file"
  }
}
EOF
)
    
    # Replace variables in the payload
    payload=$(echo "$payload" | sed "s/\$event_id/$event_id/g" | sed "s/\$video_file/$video_file/g")
    
    echo "$payload" | mosquitto_pub -h mqtt -t "frigate/events" -s
    
    # Check if mosquitto_pub command succeeded
    if [ $? -eq 0 ]; then
        echo "✅ Injected test event: $event_id"
    else
        echo "❌ Failed to inject test event: $event_id"
        echo "   Check if MQTT broker is running and accessible"
        return 1
    fi
    
    echo "⏳ Waiting 10 seconds before next event..."
    sleep 10
}

# Check if mosquitto_pub is available
if ! command -v mosquitto_pub &> /dev/null; then
    echo "❌ mosquitto_pub not found. Installing mosquitto-clients..."
    apt-get update && apt-get install -y mosquitto-clients
fi

# Inject test events for all videos in /app/test_videos/
echo ""
echo "Injecting test events for all videos in /app/test_videos/..."

for video_path in /app/test_videos/*; do
    video_file=$(basename "$video_path")
    event_id="test_${video_file%.*}_$(date +%s%N)"
    description="Test event for $video_file"
    inject_test_event "$event_id" "$video_file" "$description"
done

echo ""
echo "✅ Test events injected successfully!"
echo "Check the Sunny Osprey logs to see the analysis results."
