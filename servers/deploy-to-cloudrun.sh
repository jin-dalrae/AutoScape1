#!/bin/bash
set -e

PROJECT="autoscape-dfc00"
REGION="us-central1"
SERVICE="rag-api"
IMAGE="gcr.io/${PROJECT}/${SERVICE}:latest"
QDRANT_URL="https://da9b95c9-1480-44c3-af6d-397ee9121aad.us-west-2-0.aws.cloud.qdrant.io"

echo "=== AutoScape RAG Backend Deploy to Cloud Run ==="
echo "Project: $PROJECT"
echo "Service: $SERVICE"
echo

# Ensure we're in the servers dir
cd "$(dirname "$0")"

echo "0. Ensuring gcloud auth for GCR / Artifact Registry..."
gcloud auth login --update-adc || true
gcloud config set project $PROJECT
gcloud auth configure-docker gcr.io --quiet

# Grant permission if needed (idempotent)
echo "   Checking/adding Artifact Registry writer permission..."
gcloud projects add-iam-policy-binding $PROJECT \
  --member="user:$(gcloud config get-value account)" \
  --role="roles/artifactregistry.writer" \
  --condition=None 2>/dev/null || true

# Get the default Compute Engine service account used by Cloud Run revisions
PROJECT_NUMBER=$(gcloud projects describe $PROJECT --format="value(projectNumber)")
SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

echo "   Granting Secret Manager Secret Accessor role to Cloud Run service account ($SA)..."
gcloud secrets add-iam-policy-binding QDRANT_API_KEY \
  --member="serviceAccount:${SA}" \
  --role="roles/secretmanager.secretAccessor" \
  --project=$PROJECT 2>/dev/null || true

gcloud secrets add-iam-policy-binding GEMINI_API_KEY \
  --member="serviceAccount:${SA}" \
  --role="roles/secretmanager.secretAccessor" \
  --project=$PROJECT 2>/dev/null || true

echo "1. Building Docker image for linux/amd64 (required by Cloud Run)..."
docker build --platform linux/amd64 -t $IMAGE .

echo "2. Pushing image..."
docker push $IMAGE

echo "3. Deploying to Cloud Run (without PORT in env - Cloud Run sets it)..."
gcloud run deploy $SERVICE \
  --image $IMAGE \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --set-env-vars "QDRANT_URL=${QDRANT_URL},PLANT_COLLECTION=autoscape-components" \
  --set-secrets "QDRANT_API_KEY=QDRANT_API_KEY:latest,GEMINI_API_KEY=GEMINI_API_KEY:latest" \
  --project=$PROJECT

echo "4. Getting service URL..."
URL=$(gcloud run services describe $SERVICE --region $REGION --project $PROJECT --format='value(status.url)')
echo "✅ Deployed successfully!"
echo "Service URL: $URL"
echo
echo "Test with:"
echo "curl $URL/health"
echo
echo "To test RAG with labor example:"
echo "curl -X POST $URL/api/enhance-with-rag -H 'Content-Type: application/json' -d '{\"plants\":[{\"name\":\"Japanese Maple\",\"quantity\":2}],\"labor\":[{\"name\":\"Site Preparation & Demolition\",\"quantity\":1}]}'"
