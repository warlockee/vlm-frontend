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
# Ensure we use all 8 GPUs
export CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7

nohup python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 > ../backend.log 2>&1 &
BACKEND_PID=$!
echo "Backend started with PID $BACKEND_PID (using Ray + vLLM)"

# Start Frontend
echo "Starting Frontend..."
cd ../frontend
nohup npm run dev -- --host > ../frontend.log 2>&1 &
FRONTEND_PID=$!
echo "Frontend started with PID $FRONTEND_PID"

echo "Service is running!"
echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:5173"
echo "Logs are in backend.log and frontend.log"
echo "Press Ctrl+C to stop..."

# Trap SIGINT to kill background processes
trap "kill $BACKEND_PID $FRONTEND_PID; exit" SIGINT

wait
