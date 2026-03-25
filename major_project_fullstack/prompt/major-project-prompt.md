# Detailed Prompt for AI / Team Execution

Use this prompt when you want an AI assistant or developer to understand and continue this Major Project exactly.

## Prompt

You are a senior full-stack engineer helping me complete a **Major Project** called:

**Intelligent Visual Monitoring System - IntelMon**

### Objective

Build one full-scale application that unifies these existing modules into a single professional system:

1. Automatic Number Plate Recognition (ANPR)
2. Crowd Anomaly Detection
3. Crowd Gathering Detection
4. Mask Compliance Detection

### Existing Codebase Context

My workspace contains existing folders with working/non-working scripts and model files.  
Do **not** randomly modify them.

Rules for existing folders:

- Touch existing files only if there is a real execution/blocking error.
- If a file is already correct, do not change it.
- Keep original project logic intact.

### Core Platform Requirements

1. **Backend must be Spring Boot + MySQL**
- JWT-based authentication
- Register + Login API
- Store user details securely (hashed passwords)
- Upload and manage videos
- Persist video metadata in MySQL
- Trigger analysis jobs for selected AI service and selected video
- Track job status: `QUEUED`, `RUNNING`, `COMPLETED`, `FAILED`

2. **Frontend must be a strong dashboard application**
- Register/Login pages
- Modern, presentation-ready UI
- Single control center for all modules
- Upload videos
- Select service + run analysis
- View all jobs and statuses
- View summary cards (videos, jobs, running, failed, completed)
- Responsive design for desktop + mobile

3. **Integration behavior**
- Backend should orchestrate existing Python scripts
- Each service should run through command execution from backend
- Store logs/output path for each job
- Handle failures gracefully and show meaningful errors

4. **Project quality expectations**
- Production-style folder structure
- Clean APIs and DTOs
- Exception handling
- Environment-based configs
- README with run instructions
- Docker Compose support (MySQL + backend + frontend)

### Non-Negotiables

- Keep the old project folders safe.
- Create new files/folders for integration app.
- Make this suitable to present as a final-year **Major Project**.
- Provide complete runnable structure, not just pseudo-code.

### Deliverables Checklist

- Spring Boot backend implementation
- MySQL entities/repositories/services/controllers
- JWT security config
- React frontend dashboard implementation
- Dockerfiles + docker-compose
- `.env.example` files
- Documentation and setup guide
- Notes on which existing files were corrected and why

### Acceptance Criteria

- User can register and login from frontend.
- Authenticated user can upload video and see it listed.
- Authenticated user can run AI analysis jobs on uploaded videos.
- Dashboard displays service list, uploaded videos, job statuses, and summary metrics.
- Existing model folders remain intact except minimal error fixes.
- Project is presentable as a complete Major Project demo.
