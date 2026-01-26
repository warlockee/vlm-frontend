"""
VLM API Gateway (Port 8000)

Features:
- Lightweight Proxy
- Decoupled from vLLM engine (running on 8001)
- Handles routing for Student/Teacher models
"""
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
import logging
import time
import httpx
import base64
import uuid
import json
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vlm-gateway")

app = FastAPI(title="Visual Understanding Gateway")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
# Student model: via SSH tunnel to a100_2:8002 -> localhost:8003 (OpenAI format)
# Teacher model: localhost:8002 (custom /inference format)
STUDENT_URL = os.getenv("STUDENT_URL", "http://localhost:8003/v1/chat/completions")  # a100_2 via SSH tunnel
STUDENT_MODEL = os.getenv("STUDENT_MODEL", "OpenGVLab/InternVL2-1B")
TEACHER_URL = os.getenv("TEACHER_URL", "http://localhost:8002/inference")  # local teacher

# Dataset Storage
DATASET_DIR = os.path.join(os.path.dirname(__file__), "datasets")
IMG_DIR = os.path.join(DATASET_DIR, "images")
LOG_DIR = os.path.join(DATASET_DIR, "logs")
SFT_FILE = os.path.join(LOG_DIR, "sft_dataset.jsonl")
DPO_FILE = os.path.join(LOG_DIR, "dpo_dataset.jsonl")

# Ensure directories exist
os.makedirs(IMG_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

@app.get("/health")
async def health_check():
    # Check Gateway health + Teacher Backend health (port 8002)
    backend_status = "unknown"
    model_loaded = False
    try:
        async with httpx.AsyncClient() as client:
            # Teacher model runs on port 8002
            resp = await client.get(f"http://localhost:8002/health", timeout=2.0)
            if resp.status_code == 200:
                data = resp.json()
                backend_status = "connected"
                model_loaded = data.get("model_loaded", False)
    except Exception:
        backend_status = "disconnected"

    return {
        "status": "ok",
        "gateway": "active",
        "backend_connection": backend_status,
        "model_loaded": model_loaded
    }

@app.post("/inference")
async def inference(
    file: UploadFile = File(...),
    prompt: str = Form(...)
):
    # Proxy to Teacher Backend (default)
    async with httpx.AsyncClient() as client:
        try:
            content = await file.read()
            files = {'file': (file.filename, content, file.content_type)}
            data = {'prompt': prompt + " response in json format"}

            resp = await client.post(TEACHER_URL, data=data, files=files, timeout=120.0)
            if resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail=resp.text)
            return resp.json()
        except Exception as e:
            logger.error(f"Backend Proxy Error: {e}")
            raise HTTPException(status_code=500, detail="Backend unavailable")

@app.post("/student")
async def predict_student(
    file: UploadFile = File(...),
    query: str = Form(...)
):
    """
    Adapter endpoint for the Student model (OpenAI-compatible vLLM).
    Converts image to base64 and sends chat completion request.
    """
    start_time = time.time()
    try:
        content = await file.read()
        # Convert to base64
        img_base64 = base64.b64encode(content).decode('utf-8')
        # Determine mime type
        content_type = file.content_type or 'image/jpeg'

        # Build OpenAI-compatible request
        payload = {
            "model": STUDENT_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": f"data:{content_type};base64,{img_base64}"}},
                        {"type": "text", "text": query + " response in json format"}
                    ]
                }
            ],
            "max_tokens": 1024,
            "temperature": 0.0
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(STUDENT_URL, json=payload, timeout=120.0)

            if resp.status_code != 200:
                return {"response": f"Error: Status {resp.status_code} - {resp.text}", "latency": 0.0}

            result = resp.json()
            # Extract response from OpenAI format
            response_text = result.get("choices", [{}])[0].get("message", {}).get("content", "")

            duration = time.time() - start_time
            return {
                "response": response_text,
                "latency": round(duration, 2)
            }
    except Exception as e:
        logger.error(f"Student Proxy Error: {e}")
        return {"response": f"Error: {str(e)}", "latency": 0.0}

@app.post("/teacher")
async def predict_teacher(
    file: UploadFile = File(...),
    query: str = Form(...)
):
    """
    Proxy endpoint for the Teacher model.
    Forwards request to TEACHER_URL.
    """
    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded")
        
    start_time = time.time()
    try:
        content = await file.read()
        async with httpx.AsyncClient() as client:
            files = {'file': (file.filename, content, file.content_type)}
            data = {'prompt': query + " response in json format"}
            
            # TEACHER_URL is external (or different port)
            response = await client.post(TEACHER_URL, data=data, files=files, timeout=60.0)
            
            if response.status_code != 200:
                return {"response": f"Error: Status {response.status_code} - {response.text}", "latency": 0.0}
            
            # Try to parse response
            try:
                res_json = response.json()
                content_str = ""
                if "text" in res_json: content_str = res_json["text"]
                elif "choices" in res_json: content_str = res_json["choices"][0]["message"]["content"]
                elif "response" in res_json: content_str = res_json["response"]
                else: content_str = str(res_json)
            except:
                content_str = response.text
                
            duration = time.time() - start_time
            return {
                "response": content_str,
                "latency": round(duration, 2)
            }
            
    except Exception as e:
        logger.error(f"Teacher Proxy Error: {e}")
        return {"response": f"Error: {str(e)}", "latency": 0.0}

@app.post("/feedback/sft")
async def feedback_sft(
    file: UploadFile = File(...),
    query: str = Form(...),
    response: str = Form(...),
    model_name: str = Form(...),
    is_pass: bool = Form(...)
):
    try:
        # Save image
        ext = file.filename.split('.')[-1] if '.' in file.filename else 'jpg'
        img_id = f"{uuid.uuid4()}.{ext}"
        img_path = os.path.join(IMG_DIR, img_id)
        
        content = await file.read()
        with open(img_path, "wb") as f:
            f.write(content)
            
        record = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "image": img_id},
                        {"type": "text", "text": query}
                    ]
                },
                {
                    "role": "assistant",
                    "content": response
                }
            ],
            "model": model_name,
            "label": "pass" if is_pass else "fail"
        }
        
        with open(SFT_FILE, "a") as f:
            f.write(json.dumps(record) + "\n")
            
        return {"status": "ok", "id": record["id"]}
    except Exception as e:
        logger.error(f"SFT Feedback Error: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/feedback/dpo")
async def feedback_dpo(
    file: UploadFile = File(...),
    query: str = Form(...),
    response_winner: str = Form(...),
    response_loser: str = Form(...),
    model_winner: str = Form(...),
    model_loser: str = Form(...),
    comment: str = Form(None)
):
    try:
        # Save image
        ext = file.filename.split('.')[-1] if '.' in file.filename else 'jpg'
        img_id = f"{uuid.uuid4()}.{ext}"
        img_path = os.path.join(IMG_DIR, img_id)
        
        content = await file.read()
        with open(img_path, "wb") as f:
            f.write(content)
            
        record = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "chosen": [
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "image": img_id},
                        {"type": "text", "text": query}
                    ]
                },
                {
                    "role": "assistant",
                    "content": response_winner
                }
            ],
            "rejected": [
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "image": img_id},
                        {"type": "text", "text": query}
                    ]
                },
                {
                    "role": "assistant",
                    "content": response_loser
                }
            ],
            "metadata": {
                "winner_model": model_winner,
                "loser_model": model_loser,
                "comment": comment
            }
        }
        
        with open(DPO_FILE, "a") as f:
            f.write(json.dumps(record) + "\n")
            
        return {"status": "ok", "id": record["id"]}
    except Exception as e:
        logger.error(f"DPO Feedback Error: {e}")
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
