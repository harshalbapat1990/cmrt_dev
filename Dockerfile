# Backend
FROM python:3.11-slim
WORKDIR /app
COPY app/requirements.txt .
RUN pip install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org -r requirements.txt

# Copy backend + frontend build
COPY app/app.py .

# Run FastAPI
EXPOSE 5001
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5001"]
