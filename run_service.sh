#!/bin/bash
# Start Backend
echo "Starting Backend..."
cd backend
# Set PYTHONPATH to include the project root so vlm package can be imported
export PYTHONPATH=$PYTHONPATH:/home/ec2-user/fsx
# Start Backend
pip install -r requirements.txt

# Ray Cleanup and Optimization for vLLM
echo "Cleaning up Ray cluster and old processes..."
pkill -f "uvicorn" || true
ray stop --force || true
pkill -f "ray::" || true

# Start Inference Server (Port 8002)
echo "Starting Inference Server (vLLM on 8002)..."
# Ensure we use all 8 GPUs for Inference
export CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7
nohup python3 -m uvicorn vlm_server:app --host 0.0.0.0 --port 8002 > ../vlm_inference.log 2>&1 &
INFERENCE_PID=$!
echo "Inference Server started with PID $INFERENCE_PID"

# Wait a bit for inference init (optional, but good practice)
sleep 2

# Start Gateway (Port 8000)
echo "Starting Gateway..."
# Gateway doesn't need GPUs
export CUDA_VISIBLE_DEVICES=""
# Update Envs for local run
export INFERENCE_URL="http://localhost:8002/inference"
export TEACHER_URL="http://localhost:8002/inference"

nohup python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 > ../backend.log 2>&1 &
BACKEND_PID=$!
echo "Gateway started with PID $BACKEND_PID"

# Start Frontend
echo "Starting Frontend..."
cd ../frontend
nohup npm run dev -- --host > ../frontend.log 2>&1 &
FRONTEND_PID=$!
echo "Frontend started with PID $FRONTEND_PID"

echo "Service is running!"
echo "Gateway: http://localhost:8000"
echo "Inference: http://localhost:8002"
echo "Frontend: http://localhost:5173"
echo "Logs: backend.log, vlm_inference.log, frontend.log"
echo "Press Ctrl+C to stop..."

# Trap SIGINT to kill background processes
trap "kill $BACKEND_PID $FRONTEND_PID $INFERENCE_PID; exit" SIGINT

wait
