FROM nvidia/cuda:12.8.1-cudnn-runtime-ubuntu24.04

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Grafana configuration (can be overridden at runtime)
ENV GRAFANA_HOST=""
ENV GRAFANA_USERNAME=""
ENV GRAFANA_PASSWORD=""
ENV GRAFANA_ORG_ID="1"
ENV VIDEO_CLIP_BASE_URL="https://sbnb-to-be-filled-by-o-vm-gentle-smart-finch.tail334b4d.ts.net:8971/explore"

# Install system dependencies and Python
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    python3-venv \
    gcc \
    g++ \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    git \
    curl \
    mosquitto-clients \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Create and activate a Python virtual environment
RUN python3 -m venv /venv
ENV PATH="/venv/bin:$PATH"

# Upgrade pip in venv
RUN /venv/bin/pip install --upgrade pip

# Install PyTorch nightly first (CUDA 12.9)
RUN /venv/bin/pip install --no-cache-dir --index-url https://download.pytorch.org/whl/nightly/cu129 torch torchvision torchaudio

# Install other Python dependencies in venv
RUN /venv/bin/pip install --no-cache-dir -r requirements.txt

# Copy source code and necessary files
COPY src/ ./src/
COPY setup.py .
COPY README.md .
COPY prompt.txt .
COPY system_prompt.txt .
COPY tests/ ./tests/

# Create test videos directory and copy test files
RUN mkdir -p /app/test_videos
COPY tests/data/ /app/test_videos/

# Copy injection script and make it executable
COPY inject_test_events.sh /app/
RUN chmod +x /app/inject_test_events.sh

# Install the package in development mode in venv
RUN /venv/bin/pip install -e .

# Set the default command to run the MQTT processor using venv's python
CMD ["/venv/bin/python", "src/sunny_osprey/main.py"] 