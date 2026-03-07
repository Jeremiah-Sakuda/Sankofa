#!/bin/bash
# Sankofa — Google Cloud Run Deployment Script
# Prerequisites: gcloud CLI installed and authenticated

set -e

PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-sankofa-heritage}"
REGION="${GOOGLE_CLOUD_LOCATION:-us-central1}"

echo "=== Deploying Sankofa to Google Cloud Run ==="
echo "Project: $PROJECT_ID"
echo "Region: $REGION"

# Deploy Backend
echo ""
echo "--- Deploying Backend API ---"
cd backend
gcloud run deploy sankofa-api \
  --source . \
  --region "$REGION" \
  --project "$PROJECT_ID" \
  --allow-unauthenticated \
  --set-env-vars "GOOGLE_CLOUD_PROJECT=$PROJECT_ID,GOOGLE_CLOUD_LOCATION=$REGION,GOOGLE_GENAI_USE_VERTEXAI=True,FRONTEND_URL=https://sankofa-frontend-*-uc.a.run.app" \
  --min-instances 1 \
  --max-instances 5 \
  --memory 1Gi \
  --timeout 300

BACKEND_URL=$(gcloud run services describe sankofa-api --region "$REGION" --project "$PROJECT_ID" --format "value(status.url)")
echo "Backend deployed at: $BACKEND_URL"

# Deploy Frontend
echo ""
echo "--- Deploying Frontend ---"
cd ../frontend
gcloud run deploy sankofa-frontend \
  --source . \
  --region "$REGION" \
  --project "$PROJECT_ID" \
  --allow-unauthenticated \
  --set-env-vars "NEXT_PUBLIC_API_URL=$BACKEND_URL" \
  --build-arg "NEXT_PUBLIC_API_URL=$BACKEND_URL" \
  --min-instances 1 \
  --max-instances 3 \
  --memory 512Mi

FRONTEND_URL=$(gcloud run services describe sankofa-frontend --region "$REGION" --project "$PROJECT_ID" --format "value(status.url)")
echo "Frontend deployed at: $FRONTEND_URL"

# Update backend CORS with actual frontend URL
echo ""
echo "--- Updating Backend CORS ---"
cd ../backend
gcloud run services update sankofa-api \
  --region "$REGION" \
  --project "$PROJECT_ID" \
  --update-env-vars "FRONTEND_URL=$FRONTEND_URL"

echo ""
echo "=== Deployment Complete ==="
echo "Frontend: $FRONTEND_URL"
echo "Backend API: $BACKEND_URL"
echo "API Docs: $BACKEND_URL/docs"
