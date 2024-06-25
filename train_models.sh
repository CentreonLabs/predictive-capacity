#!/bin/sh

# URL of the forecast_api training endpoint
FORECAST_API_URL="http://backend:7000/forecast"

# Make the API call
curl -X POST "${FORECAST_API_URL}" -H "Content-Type: application/json" -s >> /var/log/train_models.log 2>&1