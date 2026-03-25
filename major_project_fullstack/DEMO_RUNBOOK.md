# IntelMon Major Project Demo Runbook

This guide is for running IntelMon in **2-terminal local mode** (recommended for professor demo).

- Frontend runs locally on port `5173`
- Backend runs locally on port `8080`
- MySQL + Redis run in Docker (infra only)

## 1) Project Location

Workspace root:

```bash
/Users/saidharahasrao/Major/major_project_fullstack
```

## 2) What Gets Stored (Very Important)

### Database (MySQL)

- MySQL container port: `3307`
- Database name: `major_monitoring`
- Main tables:
  - `app_users`
  - `video_assets`
  - `analysis_jobs`
  - `live_alert_events`

### Files on Disk

- Uploaded videos:
  - `/Users/saidharahasrao/Major/major_project_fullstack/storage/videos`
- Processed result videos:
  - `/Users/saidharahasrao/Major/major_project_fullstack/storage/results`

## 3) Terminal 0 (Infra): Start MySQL + Redis

Open Terminal 0 and run:

```bash
cd /Users/saidharahasrao/Major/major_project_fullstack
docker compose up -d mysql redis
docker compose ps
```

Expected: `major_project_mysql` and `major_project_redis` should be `Up (healthy)`.

## 4) Terminal 1 (Backend): Start Spring Boot Locally

Open Terminal 1 and run:

```bash
cd /Users/saidharahasrao/Major/major_project_fullstack/backend
SPRING_DATASOURCE_URL='jdbc:mysql://localhost:3307/major_monitoring?createDatabaseIfNotExist=true&useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=UTC' \
SPRING_DATASOURCE_USERNAME='root' \
SPRING_DATASOURCE_PASSWORD='root' \
SPRING_DATA_REDIS_HOST='localhost' \
SPRING_DATA_REDIS_PORT='6379' \
APP_WORKSPACE_ROOT='/Users/saidharahasrao/Major' \
APP_VIDEO_STORAGE='/Users/saidharahasrao/Major/major_project_fullstack/storage/videos' \
APP_RESULT_STORAGE='/Users/saidharahasrao/Major/major_project_fullstack/storage/results' \
APP_PYTHON_BIN='python3' \
mvn spring-boot:run
```

Health check in a separate tab:

```bash
curl -s http://localhost:8080/actuator/health
```

Expected:

```json
{"status":"UP"}
```

## 5) Terminal 2 (Frontend): Start React UI Locally

Open Terminal 2 and run:

```bash
cd /Users/saidharahasrao/Major/major_project_fullstack/frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

Open browser:

```text
http://localhost:5173
```

## 6) Demo Login Flow

1. Register a new account from UI.
2. Login.
3. You should land on Dashboard.

If needed, clear stale browser auth:
- logout, then hard refresh (`Cmd + Shift + R`), login again.

## 7) Professor Demo Sequence (Recommended)

1. Dashboard:
   - Show totals, jobs, failed/completed counts.
2. Upload Video:
   - Upload sample `.mp4`.
3. Run Analysis:
   - Trigger `MASK_DETECTION` (quick)
   - Trigger `CROWD_GATHERING`
   - Trigger `ANPR` (can take longer on CPU)
4. Analysis Jobs:
   - Show status transitions `QUEUED -> RUNNING -> COMPLETED/FAILED`
5. Results Viewer:
   - Play output video.
6. Live Monitoring:
   - Start camera or file mode.
   - Start Live Analysis.
   - Show overlay boxes + alert banner + live events.
7. Analytics/Profile:
   - Show metrics and account details.

## 8) Verify Data Is Actually Stored (Proof for Evaluation)

### DB Proof

Run:

```bash
cd /Users/saidharahasrao/Major/major_project_fullstack
docker exec major_project_mysql mysql -uroot -proot -D major_monitoring -e "SELECT COUNT(*) AS users FROM app_users; SELECT COUNT(*) AS videos FROM video_assets; SELECT COUNT(*) AS jobs FROM analysis_jobs; SELECT COUNT(*) AS live_alerts FROM live_alert_events;"
```

### Latest Analysis Jobs

```bash
cd /Users/saidharahasrao/Major/major_project_fullstack
docker exec major_project_mysql mysql -uroot -proot -D major_monitoring -e "SELECT id,service_type,status,error_message,output_location,created_at FROM analysis_jobs ORDER BY id DESC LIMIT 10;"
```

### Filesystem Proof

```bash
ls -lh /Users/saidharahasrao/Major/major_project_fullstack/storage/videos | head
ls -lh /Users/saidharahasrao/Major/major_project_fullstack/storage/results | head
```

## 9) Common Issues and Fast Fixes

### Issue A: `Input video does not exist ... /storage/videos/...`

Cause: old/stale path + wrong runtime mode.

Fix:
1. Ensure backend is running in local mode using Terminal 1 command above.
2. Re-upload the video once from UI.
3. Run analysis again.

### Issue B: Port `8080` already in use

Find and kill process:

```bash
lsof -nP -iTCP:8080 -sTCP:LISTEN
kill <PID>
```

Then restart backend.

### Issue C: Port `5173` already in use

```bash
lsof -nP -iTCP:5173 -sTCP:LISTEN
kill <PID>
```

Restart frontend.

### Issue D: MySQL connection error in backend

Check infra:

```bash
cd /Users/saidharahasrao/Major/major_project_fullstack
docker compose ps
docker compose up -d mysql redis
```

### Issue E: Live Monitoring says disconnected

1. Verify backend health.
2. Refresh UI.
3. Start camera and click Start Live Analysis again.
4. Confirm browser camera permissions are allowed.

## 10) Stop Everything After Demo

### Stop frontend/backend local terminals

- In Terminal 1 and 2: press `Ctrl + C`

### Stop infra containers

```bash
cd /Users/saidharahasrao/Major/major_project_fullstack
docker compose stop mysql redis
```

## 11) Optional: Full Docker Mode (Not Recommended for Your Current Demo)

You can run all via Docker, but your current professor demo is more stable in 2-terminal local mode.

## 12) Final Demo Checklist

- [ ] MySQL + Redis healthy
- [ ] Backend `UP` on `8080`
- [ ] Frontend on `5173`
- [ ] Upload works
- [ ] At least one completed analysis job
- [ ] Results video playable
- [ ] Live monitoring overlay + events visible
- [ ] DB rows visible in `analysis_jobs` and `live_alert_events`

