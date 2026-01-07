from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import shutil
import os
import uuid
import logging
from contextlib import asynccontextmanager
from inference_engine import engine

# Logging Setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vlm-backend")

# Lifespan manager to load model on startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up VLM Backend...")
    try:
        engine.load_model()
    except Exception as e:
        logger.error(f"Critical Error loading model: {e}")
        # In a real app we might want to shut down, but here we'll log it.
    yield
    logger.info("Shutting down VLM Backend...")

app = FastAPI(title="Visual Understanding Demo", lifespan=lifespan)

# CORS (Allowing all for dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "/tmp/vlm_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.get("/health")
def health_check():
    return {"status": "ok", "model_loaded": engine.model is not None}

@app.post("/inference")
async def inference(
    file: UploadFile = File(...),
    prompt: str = Form(...)
):
    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded")
    
    # Generate unique filename to avoid collisions
    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        logger.info(f"File saved to {file_path}")
        
        response_text = engine.predict(file_path, prompt)
        
        # Cleanup (Optional: keep for debugging or cleanup immediately)
        # os.remove(file_path) 
        
        return {"response": response_text}
        
    except Exception as e:
        logger.error(f"Inference error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
