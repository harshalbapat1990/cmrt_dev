# Simple single-stage Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org -r requirements.txt

# Copy application code
COPY . .

# Ensure entrypoint is executable
RUN chmod +x /app/entrypoint.sh

# Expose port
EXPOSE 8000


ENV APP_MODULE=app.main:app \
    APP_PORT=8000 \
    APP_HOST=0.0.0.0

# Apply any pending Alembic revisions before the API starts.
ENTRYPOINT ["/app/entrypoint.sh"]
