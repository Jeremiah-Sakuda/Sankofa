# Deployment (Cloud Run + Firestore)

## One-command deploy

From the repo root, with `gcloud` CLI installed and authenticated:

```bash
export GOOGLE_CLOUD_PROJECT=your-project-id
export GOOGLE_CLOUD_LOCATION=us-central1
./deploy.sh
```

This deploys the backend (`sankofa-api`) and frontend (`sankofa-frontend`) to Cloud Run, then updates the backend CORS with the frontend URL.

## Firestore setup (required for production)

The backend uses Firestore for session persistence when `USE_FIRESTORE=True` (set in `deploy.sh`). Without it, sessions are in-memory and are lost on restart.

1. **Enable Firestore API** (if not already):
   ```bash
   gcloud services enable firestore.googleapis.com --project=YOUR_PROJECT_ID
   ```
   In the [Firestore console](https://console.cloud.google.com/firestore), choose **Native mode** if prompted.

2. **Grant the Cloud Run service account access**  
   After the first deploy, get the service account used by Cloud Run:
   ```bash
   gcloud run services describe sankofa-api --region=us-central1 --project=YOUR_PROJECT_ID --format="value(spec.template.spec.serviceAccountName)"
   ```
   If empty, Cloud Run uses the default compute service account:  
   `PROJECT_NUMBER-compute@developer.gserviceaccount.com`  
   Grant it the **Cloud Datastore User** role (Firestore uses this role):
   ```bash
   PROJECT_NUMBER=$(gcloud projects describe YOUR_PROJECT_ID --format="value(projectNumber)")
   gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
     --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
     --role="roles/datastore.user"
   ```

3. **Redeploy** if you had already deployed before enabling Firestore; the backend will then use Firestore for sessions.

## Environment variables (production)

Set by `deploy.sh` for the backend:

- `ENVIRONMENT=production`
- `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`
- `GOOGLE_GENAI_USE_VERTEXAI=True` (Vertex AI for Gemini)
- `USE_FIRESTORE=True`
- `FRONTEND_URL` (updated after frontend deploy for CORS)

Secrets (e.g. API keys) should be set via Secret Manager and mounted or passed as env, not in the script.
