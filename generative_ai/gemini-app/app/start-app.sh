#!/usr/bin/env bash

echo "Starting App"

streamlit run Chat.py --server.port 8080 --runner.magicEnabled False -- --guard_model_deployment_id "YOUR-GUARD-MODEL-DEPLOYMENT-ID" --text_model_deployment_id "YOUR-GEMINI-PRO-MODEL-DEPLOYMENT-ID" --multimodal_model_deployment_id "YOUR-GEMINI-PRO-VISION-MODEL-DEPLOYMENT-ID"
