# VLM Frontend Developer Manual

This document details the architecture, configuration, and development workflow for the **VLM Frontend** application, specifically following the merge of the VLM Distillation Workbench features.

## Architecture Overview

The system has been consolidated into a **Single Frontend** and a **Unified Backend Gateway**.

```mermaid
graph LR
    User[User Browser]
    Frontend[React Frontend<br/>(Port 5173)]
    Backend[FastAPI Gateway<br/>(Port 8000)]
    Student[Local vLLM Model<br/>(Internal)]
    Teacher[Remote Teacher Model<br/>(Port 8001)]

    User -->|Default Route /| Frontend
    User -->|Route /compare| Frontend
    Frontend -->|/api/*| Backend
    Backend -->|/student| Student
    Backend -->|/teacher| Teacher
```

### 1. Unified Backend (`/backend`)

The backend (running on port **8000**) acts as both the inference server for the local model and a gateway proxy for the remote teacher model.

*   **Entry Point**: `main.py`
*   **Endpoints**:
    *   `POST /inference`: Legacy endpoint for the Home Page (inference only).
    *   `POST /student`: Endpoint for the Comparison Page (Student 1.5B model). Returns `{ "response": "...", "latency": ... }`.
    *   `POST /teacher`: Proxy endpoint for the Comparison Page (Teacher 32B model). Forwards requests to `TEACHER_URL`.

**Configuration**:
*   `TEACHER_URL`: Environment variable defining the remote teacher address. Default: `http://localhost:8001/inference`.

### 2. Frontend (`/frontend`)

The frontend is a Vite + React application using `react-router-dom` for navigation.

*   **Pages**:
    *   `HomePage.jsx` (`/`): The standard single-image analysis interface.
    *   `ComparisonPage.jsx` (`/compare`): The side-by-side model comparison workbench.
*   **Routing**: Defined in `App.jsx`.
*   **Styles**:
    *   `index.css`: Global styles and Home Page styles.
    *   `comparison.css`: Scoped styles for the Comparison Page (isolated using `.comparison-page` class).
*   **Proxying**: `vite.config.js` proxies all `/api` requests to the local backend at `http://localhost:8000`.

## Development Workflow

### Prerequisites
*   Python 3.10+
*   Node.js 18+

### 1. Start the Backend

 Navigate to the backend directory:
 ```bash
 cd backend
 ```

 Install dependencies (if new):
 ```bash
 pip install -r requirements.txt
 ```

 Start the server:
 ```bash
 # Optional: Set custom teacher URL
 export TEACHER_URL="http://localhost:8001/inference"
 
 python3 main.py
 ```
 *The backend will start on `http://0.0.0.0:8000` and load the local vLLM model.*

### 2. Start the Frontend

 Navigate to the frontend directory:
 ```bash
 cd frontend
 ```

 Install dependencies (if new):
 ```bash
 npm install
 ```

 Start the development server:
 ```bash
 npm run dev
 ```
 *Access the application at `http://localhost:5173` (or the port shown in the terminal).*

## Troubleshooting

### Teacher Model Not Responding
If the "Teacher" panel in the Comparison Page hangs or errors:
1.  Check if `TEACHER_URL` in the backend is correct.
2.  Ensure the SSH tunnel to the teacher node (e.g., `a100_1`) is active and forwarding port 8001.
    *   Example tunnel: `ssh -L 8001:localhost:8000 user@remote-node` (adjust ports as needed).
3.  Verify the Teacher Service is running on the remote node.

### Backend Connection Refused
If the Frontend says "Backend not reachable":
1.  Ensure `python3 main.py` is running and healthy.
2.  Check `vite.config.js` proxy settings if you changed the backend port.
