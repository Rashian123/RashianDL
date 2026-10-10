# Use a lightweight Python image
FROM python:3.12-slim

# Install system dependencies
# ffmpeg is critical for merging video/audio and converting to MP3
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
# We install them system-wide in the container because it's already isolated
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Create downloads folder
RUN mkdir -p downloads

# Expose Flask port
EXPOSE 6713

# Run the application
# Using 0.0.0.0 to make it accessible from outside the container
CMD ["python", "app.py"]
