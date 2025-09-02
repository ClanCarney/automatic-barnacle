# Use slim Python and run as non-root
FROM python:3.11-slim

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY src/main.py /app/
COPY settings.txt /app/
COPY tokens.txt /app/

# Create non-root user
RUN useradd -m appuser \
 && chown -R appuser:appuser /app

USER appuser

# Expose the port
EXPOSE 3000

ENV PYTHONUNBUFFERED=1

# Run the Flask app
CMD ["python", "main.py"]
