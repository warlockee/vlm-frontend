"""
High-Performance VLM Inference Server (Port 8001)

Features:
- Dedicated vLLM Engine Host
- Tensor parallelism across 8 GPUs
- Continuous batching
"""
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
import shutil
import os
import uuid
import logging
import time
from contextlib import asynccontextmanager
from inference_engine import vllm_engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vlm-inference-server")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up vLLM Inference Server...")
    try:
        vllm_engine.load_model()
    except Exception as e:
        logger.error(f"Critical Error loading model: {e}")
        raise
    yield
    logger.info("Shutting down vLLM Inference Server...")

app = FastAPI(title="VLM Inference Server (vLLM)", lifespan=lifespan)

UPLOAD_DIR = "/tmp/vlm_uploads_server"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "model_loaded": vllm_engine.model is not None,
        "mode": "vllm_server",
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
        
        start_time = time.time()
        response_text = await vllm_engine.predict(file_path, prompt)
        elapsed = time.time() - start_time
        
        logger.info(f"Inference completed in {elapsed:.2f}s")
        return {"response": response_text}

    except Exception as e:
        import traceback
        logger.error(f"Inference error: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

if __name__ == "__main__":
    import uvicorn
    # Port 8002 for Inference Server (Avoids SSH tunnel on 8001)
    uvicorn.run(app, host="0.0.0.0", port=8002)
