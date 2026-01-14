#!/bin/bash
# Robust Reboot Script for VLM Service (vLLM Backup)
# Handles cleaning up both optimized (vLLM) and fallback (HF) processes.

set -e

echo "=== VLM Service Reboot Initiated ==="

# 1. Kill any process listening on port 8000
echo "[1/4] Stopping existing services..."
# Find PID on port 8000
PID=$(lsof -t -i:8000 || true)
if [ ! -z "$PID" ]; then
    echo "Found process $PID on port 8000. Terminating..."
    kill "$PID" || true
    # Wait loop
    for i in {1..10}; do
        if kill -0 "$PID" 2>/dev/null; then
            echo "Waiting for PID $PID to exit... ($i/10)"
            sleep 1
        else
            echo "Process $PID terminated."
            break
        fi
    done
    # Force kill if still alive
    if kill -0 "$PID" 2>/dev/null; then
        echo "Force killing $PID..."
        kill -9 "$PID" || true
    fi
else
    echo "No process found on port 8000."
fi

# 2. Aggressive cleanup of potential zombie names (just in case they aren't on port 8000 yet)
pkill -f "uvicorn main:app" || true
pkill -f "uvicorn main_vllm:app" || true

echo "[2a/4] Cleaning up Ray processes (GPU memory holders)..."
ray stop --force || true
pkill -f "ray::" || true 
sleep 3
# Double check GPU memory is free? (Optional, but good for robustness)


# 3. Start vLLM Backend
echo "[3/4] Starting vLLM Backend (optimized)..."
BACKEND_DIR="/home/ec2-user/fsx/vlm-frontend/backend"
cd "$BACKEND_DIR"

export CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7
export LD_LIBRARY_PATH=/usr/local/cuda/lib:/usr/local/cuda:/usr/local/cuda/lib64:/usr/local/cuda/extras/CUPTI/lib64:/usr/local/cuda/targets/x86_64-linux/lib:/opt/amazon/openmpi/lib64:/opt/amazon/efa/lib64:/opt/amazon/ofi-nccl/lib64:/usr/local/lib:/usr/lib:/lib
nohup python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 > /tmp/vlm_vllm.log 2>&1 &
NEW_PID=$!
echo "Started vLLM process with PID: $NEW_PID"

# 4. Verify Startup
echo "[4/4] Verifying Health (Timeout: 120s)..."
for i in {1..24}; do
    STATUS_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health || echo "000")
    if [ "$STATUS_CODE" -eq 200 ]; then
        echo "SUCCESS: Service is UP and Healthy!"
        curl -s http://localhost:8000/health | python3 -m json.tool
        exit 0
    fi
    echo "Waiting for health check... ($((i*5))s/120s)"
    sleep 5
done

echo "ERROR: Service failed to pass health check in 120s."
echo "Tail of logs:"
tail -n 20 /tmp/vlm_vllm.log
exit 1
