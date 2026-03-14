$ErrorActionPreference = "Stop"

$REGION = "us-central1"
$PROJECT_ID = "sankofa-489521"
$GCLOUD = "C:\Users\jerem\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"

Write-Host "=== Deploying Sankofa to Google Cloud Run (Windows) ==="
Write-Host "Project: $PROJECT_ID"
Write-Host "Region: $REGION"

# Deploy Backend
Write-Host ""
Write-Host "--- Deploying Backend API ---"
Set-Location "c:\Users\jerem\Desktop\2025 Fall Projects\Sankofa\backend"

& $GCLOUD run deploy sankofa-api --source . --region $REGION --project $PROJECT_ID --allow-unauthenticated --quiet --set-env-vars "ENVIRONMENT=production,GOOGLE_CLOUD_PROJECT=$PROJECT_ID,GOOGLE_CLOUD_LOCATION=$REGION,GOOGLE_GENAI_USE_VERTEXAI=True,USE_FIRESTORE=True,FRONTEND_URL=https://sankofa-frontend-placeholder.a.run.app" --min-instances 1 --max-instances 5 --memory 1Gi --timeout 300

$BACKEND_URL = (& $GCLOUD run services describe sankofa-api --region $REGION --project $PROJECT_ID --format "value(status.url)").Trim()
Write-Host "Backend deployed at: $BACKEND_URL"

# Deploy Frontend
Write-Host ""
Write-Host "--- Deploying Frontend ---"
Set-Location "c:\Users\jerem\Desktop\2025 Fall Projects\Sankofa\frontend"

& $GCLOUD run deploy sankofa-frontend --source . --region $REGION --project $PROJECT_ID --allow-unauthenticated --quiet --set-env-vars "NEXT_PUBLIC_API_URL=$BACKEND_URL" --set-build-env-vars "NEXT_PUBLIC_API_URL=$BACKEND_URL" --min-instances 1 --max-instances 3 --memory 512Mi

$FRONTEND_URL = (& $GCLOUD run services describe sankofa-frontend --region $REGION --project $PROJECT_ID --format "value(status.url)").Trim()
Write-Host "Frontend deployed at: $FRONTEND_URL"

# Update backend CORS
Write-Host ""
Write-Host "--- Updating Backend CORS ---"
Set-Location "c:\Users\jerem\Desktop\2025 Fall Projects\Sankofa\backend"

& $GCLOUD run services update sankofa-api --region $REGION --project $PROJECT_ID --update-env-vars "FRONTEND_URL=$FRONTEND_URL"

Write-Host ""
Write-Host "=== Deployment Complete ==="
Write-Host "Frontend: $FRONTEND_URL"
Write-Host "Backend API: $BACKEND_URL"
Write-Host "API Docs: $BACKEND_URL/docs"
