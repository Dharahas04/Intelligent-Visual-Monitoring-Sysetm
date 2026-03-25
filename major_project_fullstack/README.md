# Intelligent Visual Monitoring System - IntelMon

IntelMon is a unified major-project platform that integrates four AI services into one production-style workflow:

- Automatic Number Plate Recognition (ANPR)
- Crowd Anomaly Detection
- Crowd Gathering Detection
- Mask Detection

The platform includes:

- Spring Boot backend with JWT auth
- MySQL persistence
- Redis-backed live frame queue (with local in-memory fallback)
- React frontend dashboard with live monitoring
- Python model connectors and output video orchestration

## Core Features

- Register / Login / Profile APIs
- Video upload and metadata storage
- Async analysis job system with status tracking (`QUEUED`, `RUNNING`, `COMPLETED`, `FAILED`)
- Error-safe model execution with structured result payloads
- Results viewer for processed videos and metrics
- Analytics dashboard (status, service usage, trends)
- Live Monitoring page (webcam, start/stop stream, recording, real-time stats)

## Architecture

```text
Frontend (React + Vite)
  -> Backend REST APIs (Spring Boot)
  -> WebSocket /ws/live (real-time frame streaming)
  -> Redis queue (live frame buffering)
  -> Python service connectors (ANPR, crowd anomaly, crowd gathering, mask)
  -> MySQL (users, videos, analysis_jobs)
```

## Database Design

Main tables:

- `users`
- `videos`
- `analysis_jobs`

Relationships:

- `users` 1->N `videos`
- `users` 1->N `analysis_jobs`
- `videos` 1->N `analysis_jobs`

## API Endpoints

Authentication:

- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/auth/profile`

Video & Analysis:

- `POST /api/videos/upload`
- `GET /api/videos`
- `POST /api/analysis/run`
- `GET /api/analysis/jobs`
- `GET /api/analysis/jobs/{id}/output`

Dashboard & Services:

- `GET /api/dashboard/summary`
- `GET /api/services`
- `GET /api/live/status`

Live Stream:

- WebSocket endpoint: `ws://localhost:8080/ws/live`

## Installation & Run Guide

### 1) Clone Repository

```bash
git clone <your-repo-url>
cd major_project_fullstack
```

### 2) Start MySQL and Redis

```bash
docker compose up -d mysql redis
```

### 3) Configure Backend Environment

Copy `.env.example` in `backend/` and set values if needed.

Important environment variables:

- `SPRING_DATASOURCE_URL`
- `SPRING_DATASOURCE_USERNAME`
- `SPRING_DATASOURCE_PASSWORD`
- `APP_JWT_SECRET`
- `APP_WORKSPACE_ROOT`
- `APP_VIDEO_STORAGE`
- `APP_RESULT_STORAGE`
- `APP_PYTHON_BIN`
- `SPRING_DATA_REDIS_HOST`
- `SPRING_DATA_REDIS_PORT`
- `APP_LIVE_REDIS_ENABLED`

### 4) Setup Python Environments

Ensure required Python dependencies/models exist in linked service folders:

- `Automatic-Number-Plate-Recognition-using-YOLOv5`
- `Crowd-Anomaly-Detection-master`
- `Crowd-Gathering-Detection-main`
- `intelligent_monitoring_system/ai_service`

For connector-level dependencies:

```bash
cd connectors
pip install -r requirements.txt
```

### 5) Run Backend

```bash
cd backend
mvn spring-boot:run
```

Backend URL: `http://localhost:8080`

### 6) Run Frontend

```bash
cd ../frontend
npm install
npm run dev
```

Frontend URL: `http://localhost:5173`

### 7) Full Stack via Docker (optional)

```bash
docker compose up --build
```

## Validation / Accuracy Table

| Service | Dataset Used | Accuracy | Precision | Recall |
| --- | --- | --- | --- | --- |
| ANPR | Car Number Plate Detection (YOLOv5 val split) | 98.28% (mAP@0.5) | 98.95% | 97.76% |
| Mask Detection | Face Mask Dataset (Kaggle) | Pending benchmark | Pending benchmark | Pending benchmark |
| Crowd Anomaly | UCSD Ped2 / Avenue style benchmark | Pending formal benchmark | Pending formal benchmark | Pending formal benchmark |
| Crowd Gathering | Custom CCTV dataset | Pending formal benchmark | Pending formal benchmark | Pending formal benchmark |

Notes:

- ANPR metrics are taken from existing training artifact (`runs/train/exp/results.csv`).
- Remaining services currently have runtime validation but require dedicated labeled benchmark runs for final numeric reporting.

## Common Issues & Fixes

- `Execution failed with exit code ...`: open Job details and read `errorMessage`/payload for exact reason.
- `Output file was not generated`: verify model script writes output and storage path is writable.
- Live stream not connecting: ensure backend is running and `ws://localhost:8080/ws/live` is reachable.
- Redis unavailable: live pipeline automatically falls back to local in-memory queue.
- ANPR weak detections on some clips: retrain with domain-specific data and replace `Weights/best.pt`.

## Limitations

- Model performance depends on lighting, camera angle, and video quality.
- Real-time mode is CPU-sensitive and can lag on lower-end hardware.
- ANPR can miss blurred or distant plates.
- Live frame pipeline is queue-throttled to maintain stability under load.

## Future Work

- Cloud deployment (AWS/GCP/Azure)
- Dedicated model retraining pipelines and benchmark automation
- Multi-camera live orchestration
- Alert routing (SMS/email/push notifications)
- Edge-device optimized inference runtime

## Project Name

- Product name: **Intelligent Visual Monitoring System - IntelMon**
