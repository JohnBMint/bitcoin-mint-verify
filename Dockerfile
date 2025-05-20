FROM python:3.11-slim

# Install system dependencies for OpenCV
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
       libgl1-mesa-glx \
       libglib2.0-0 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy application files
COPY requirements.txt app.py minting_script.txt ./

# Install Python dependencies
RUN pip install --upgrade pip && pip install -r requirements.txt

# Environment and port configuration
ENV PORT=5000
EXPOSE 5000

# Launch the Flask app
CMD ["python", "app.py"]