FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY prompts/ ./prompts/
COPY config.yaml .

# Create output directory
RUN mkdir -p /app/output

# Environment variables (secrets injected at runtime, not baked into image)
ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["python", "-m", "src.cli"]
CMD ["summarise"]
