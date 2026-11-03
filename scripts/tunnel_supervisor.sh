#!/bin/bash
echo "[TUNNEL SUPERVISOR] Starting auto-restarting localtunnel on port 8000 for subdomain craftai-backend..."
while true; do
  npx localtunnel --port 8000 --subdomain craftai-backend
  EXIT_CODE=$?
  echo "[TUNNEL SUPERVISOR] localtunnel exited with code $EXIT_CODE at $(date). Restarting in 2 seconds..."
  sleep 2
done
