FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for Docker layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files
COPY . .

# Download Silero VAD model at build time
# So it doesn't download on every container start
RUN python -m livekit.agents download-files

# Expose FastAPI server port
EXPOSE 8001

# Default command — runs the agent worker
# docker-compose overrides this per-service (agent vs server)
CMD ["python", "agent.py", "start"]
