FROM python:3.11-slim

WORKDIR /app

# Copy requirements first for layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all bot files
COPY . .

# Create data and log directories
RUN mkdir -p data logs

# Default command: run the scheduler
CMD ["python", "scheduler.py"]
