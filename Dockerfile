# syntax=docker/dockerfile:1

# ---------- Stage 1: build the frontend ----------
FROM node:20-slim AS frontend-build
WORKDIR /build/frontend
COPY frontend/package.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# ---------- Stage 2: backend + built frontend ----------
FROM python:3.12-slim AS runtime

# rasterio and pyogrio ship their own GDAL inside their manylinux wheels, so
# no system GDAL/apt packages are required here -- this keeps the image
# small and the build fast, which matters for Render's free-tier build
# minutes.
WORKDIR /app

COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ ./backend/
COPY --from=frontend-build /build/frontend/dist ./frontend/dist

ENV ENVIRONMENT=production \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app/backend
EXPOSE 8000

# Render sets $PORT at runtime; default to 8000 for local `docker run`.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
