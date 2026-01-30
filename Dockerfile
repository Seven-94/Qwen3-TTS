FROM nvidia/cuda:12.1-devel-ubuntu22.04

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    git \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application
COPY app/ ./app/
COPY modele_tts/ ./modele_tts/

# Create directories
RUN mkdir -p voices cache

# Environment
ENV PYTHONPATH=/app
ENV DEVICE=cuda
ENV DTYPE=bfloat16

EXPOSE 8000

CMD ["python3", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
