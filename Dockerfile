FROM --platform=linux/amd64 python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ca-certificates \
    bash \
    curl \
    gcc \
    g++ \
    make \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip
COPY requirements.txt ./requirements.txt
# Install without TA-Lib first (optional dependency)
RUN pip install --no-cache-dir -r requirements.txt || \
    (grep -v "TA-Lib" requirements.txt > requirements_no_talib.txt && \
     pip install --no-cache-dir -r requirements_no_talib.txt)

# Copy application code
COPY . .

# Expose port 8000 for FastAPI
EXPOSE 8000

# Run the FastAPI application
CMD ["uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
