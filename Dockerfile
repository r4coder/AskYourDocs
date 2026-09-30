# One image serves both the API and the built React frontend.
#
#   docker build -t ai-document-qa .
#   docker run -p 8000:8000 ai-document-qa
#
# Gemini-only build — small, no PyTorch. NOTE: sessions live in memory, so
# run exactly ONE instance/worker.

# --- Stage 1: build the frontend --------------------------------------------
FROM node:20-alpine AS frontend-build
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm install --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# --- Stage 2: backend + built frontend ---------------------------------------
FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app/backend
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
COPY --from=frontend-build /frontend/dist /app/frontend/dist
EXPOSE 8000
# Most hosts set $PORT; fall back to 8000.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
