#!/bin/bash
# =============================================================================
# 02-enable-apis.sh - Enable Required APIs (G-002)
# =============================================================================
set -e

# Load environment
source "$(dirname "$0")/00-env.sh"

check_gcloud
print_header "Step 2: Enable Required APIs"

# Set project
gcloud config set project "$PROJECT_ID"

# List of required APIs
APIS=(
    "bigquery.googleapis.com"              # BigQuery
    "bigquerystorage.googleapis.com"       # BigQuery Storage API
    "cloudfunctions.googleapis.com"        # Cloud Functions
    "cloudscheduler.googleapis.com"        # Cloud Scheduler
    "secretmanager.googleapis.com"         # Secret Manager
    "storage.googleapis.com"               # Cloud Storage
    "cloudbuild.googleapis.com"            # Cloud Build (for Cloud Functions)
    "run.googleapis.com"                   # Cloud Run (for Cloud Functions Gen2)
    "artifactregistry.googleapis.com"      # Artifact Registry
    "logging.googleapis.com"               # Cloud Logging
    "monitoring.googleapis.com"            # Cloud Monitoring
)

echo "Will enable the following APIs in project $PROJECT_ID:"
for api in "${APIS[@]}"; do
    echo "  - $api"
done
echo ""
confirm_proceed

echo "Enabling APIs (this may take a few minutes)..."
for api in "${APIS[@]}"; do
    echo "  Enabling $api..."
    gcloud services enable "$api" --quiet
done

print_header "Step 2 Complete"
echo "All required APIs enabled."
echo ""
echo "Enabled APIs:"
gcloud services list --enabled --filter="name:($( IFS='|'; echo "${APIS[*]}" ))" --format="table(name)"
echo ""
echo "Next: Run 03-create-service-account.sh"
