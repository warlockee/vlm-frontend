"""
High-Performance VLM Backend using vLLM

Features:
- 5-10x throughput improvement over HuggingFace
- Tensor parallelism across 8 GPUs
- Continuous batching
- PagedAttention
"""
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import shutil
import os
import uuid
import logging
import time
from contextlib import asynccontextmanager
from inference_engine import vllm_engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vlm-backend-vllm")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up vLLM Backend...")
    try:
        vllm_engine.load_model()
    except Exception as e:
        logger.error(f"Critical Error loading model: {e}")
        raise
    yield
    logger.info("Shutting down vLLM Backend...")

app = FastAPI(title="Visual Understanding Demo (vLLM)", lifespan=lifespan)

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
    return {
        "status": "ok",
        "model_loaded": vllm_engine.model is not None,
        "mode": "vllm_optimized",
        "tensor_parallel_size": vllm_engine.tensor_parallel_size,
        "gpu_memory_utilization": vllm_engine.gpu_memory_utilization,
    }

@app.get("/stats")
def get_stats():
    """Get vLLM statistics."""
    return {
        "mode": "vllm",
        "tensor_parallel_size": vllm_engine.tensor_parallel_size,
        "max_num_seqs": vllm_engine.max_num_seqs,
        "gpu_memory_utilization": vllm_engine.gpu_memory_utilization,
    }

@app.post("/inference")
async def inference(
    file: UploadFile = File(...),
    prompt: str = Form(...)
):
    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded")

    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        logger.info(f"File saved to {file_path}")
        
        start_time = time.time()
        response_text = vllm_engine.predict(file_path, prompt)
        elapsed = time.time() - start_time
        
        logger.info(f"Inference completed in {elapsed:.2f}s")

        return {"response": response_text}

    except Exception as e:
        logger.error(f"Inference error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Cleanup uploaded file
        if os.path.exists(file_path):
            os.remove(file_path)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
