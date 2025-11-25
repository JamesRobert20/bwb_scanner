# Dockerfile for BWB Scanner API
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY bwb_scanner/ ./bwb_scanner/
COPY main.py .
COPY sample_options_chain.csv .

# Expose API port
EXPOSE 8000

# Run the API server
CMD ["python", "main.py", "--api"]