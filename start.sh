#!/bin/bash

# Cleanup function to kill all background processes on exit
cleanup() {
    echo "Stopping all services..."
    kill $BACKEND_PID $FRONTEND_PID $TRITON_PID 2>/dev/null
    wait $BACKEND_PID $FRONTEND_PID $TRITON_PID 2>/dev/null
    echo "All services stopped."
    exit 0
}

# Trap SIGINT and SIGTERM to run cleanup
trap cleanup SIGINT SIGTERM

echo "Starting Database..."
docker start learnq-db

echo "Starting Backend..."
cd /home/shreyansh1812/BE/LearnQ/LearnQ-Backend
if [ -d "env" ]; then
    source env/bin/activate
fi
uvicorn app.main:app --host 0.0.0.0 --port 8100 --reload &
BACKEND_PID=$!

echo "Starting Frontend..."
cd /home/shreyansh1812/BE/LearnQ/Learnq-frontend
npm run dev &
FRONTEND_PID=$!

echo "Starting Triton Server..."
podman run --device nvidia.com/gpu=all -it --rm \
  -e NVIDIA_DRIVER_CAPABILITIES=all \
  -p 8000:8000 -p 8001:8001 -p 8002:8002 \
  --shm-size=1g \
  -v /home/shreyansh1812/BE/LearnQ/Test_triton/model_repository:/models:Z \
  nvcr.io/nvidia/tritonserver:24.12-py3 \
  tritonserver --model-repository=/models --strict-model-config=false &
TRITON_PID=$!

echo "================================================="
echo "All services are running in the background."
echo "Backend: http://localhost:8100"
echo "Frontend: Check Vite output for URL"
echo "Triton: ports 8000, 8001, 8002"
echo "Press Ctrl+C to stop all services."
echo "================================================="

wait
