#!/bin/bash
# =============================================================================
# 99-cleanup.sh - Delete all GCP resources (DANGEROUS!)
# =============================================================================
# Use this script to clean up all resources when you're done with the project
# =============================================================================
set -e

# Load environment
source "$(dirname "$0")/00-env.sh"

check_gcloud
print_header "CLEANUP: Delete All GCP Resources"

echo ""
echo "!!! WARNING !!!"
echo "This will DELETE all resources in project: $PROJECT_ID"
echo ""
echo "Resources to be deleted:"
echo "  - BigQuery datasets: $BQ_DATASET_RAW, $BQ_DATASET_STAGING, $BQ_DATASET_MART"
echo "  - Cloud Storage bucket: $GCS_BUCKET"
echo "  - Secret Manager secrets (all)"
echo "  - Service Account: $SA_EMAIL"
echo "  - Cloud Functions (if any)"
echo "  - Cloud Scheduler jobs (if any)"
echo ""
echo "!!! THIS CANNOT BE UNDONE !!!"
echo ""

read -p "Type 'DELETE' to confirm: " confirmation
if [ "$confirmation" != "DELETE" ]; then
    echo "Aborted."
    exit 1
fi

echo ""
echo "Starting cleanup..."

# Set project
gcloud config set project "$PROJECT_ID"

# -----------------------------------------------------------------------------
# 1. Delete Cloud Scheduler jobs
# -----------------------------------------------------------------------------
print_header "Deleting Cloud Scheduler jobs..."
SCHEDULER_JOBS=$(gcloud scheduler jobs list --location="$REGION" --format="value(name)" 2>/dev/null || echo "")
if [ -n "$SCHEDULER_JOBS" ]; then
    for job in $SCHEDULER_JOBS; do
        echo "  Deleting scheduler job: $job"
        gcloud scheduler jobs delete "$job" --location="$REGION" --quiet || true
    done
else
    echo "  No scheduler jobs found."
fi

# -----------------------------------------------------------------------------
# 2. Delete Cloud Functions
# -----------------------------------------------------------------------------
print_header "Deleting Cloud Functions..."
FUNCTIONS=$(gcloud functions list --gen2 --region="$REGION" --format="value(name)" 2>/dev/null || echo "")
if [ -n "$FUNCTIONS" ]; then
    for func in $FUNCTIONS; do
        echo "  Deleting function: $func"
        gcloud functions delete "$func" --gen2 --region="$REGION" --quiet || true
    done
else
    echo "  No Cloud Functions found."
fi

# -----------------------------------------------------------------------------
# 3. Delete BigQuery datasets
# -----------------------------------------------------------------------------
print_header "Deleting BigQuery datasets..."
for dataset in "$BQ_DATASET_RAW" "$BQ_DATASET_STAGING" "$BQ_DATASET_MART"; do
    if bq show "$PROJECT_ID:$dataset" &>/dev/null; then
        echo "  Deleting dataset: $dataset"
        bq rm -r -f "$PROJECT_ID:$dataset" || true
    else
        echo "  Dataset $dataset not found. Skipping."
    fi
done

# -----------------------------------------------------------------------------
# 4. Delete Cloud Storage bucket
# -----------------------------------------------------------------------------
print_header "Deleting Cloud Storage bucket..."
if gsutil ls "gs://$GCS_BUCKET" &>/dev/null; then
    echo "  Deleting bucket: $GCS_BUCKET"
    gsutil -m rm -r "gs://$GCS_BUCKET" || true
else
    echo "  Bucket $GCS_BUCKET not found. Skipping."
fi

# -----------------------------------------------------------------------------
# 5. Delete Secret Manager secrets
# -----------------------------------------------------------------------------
print_header "Deleting Secret Manager secrets..."
SECRETS=$(gcloud secrets list --format="value(name)" 2>/dev/null || echo "")
if [ -n "$SECRETS" ]; then
    for secret in $SECRETS; do
        echo "  Deleting secret: $secret"
        gcloud secrets delete "$secret" --quiet || true
    done
else
    echo "  No secrets found."
fi

# -----------------------------------------------------------------------------
# 6. Delete Service Account
# -----------------------------------------------------------------------------
print_header "Deleting Service Account..."
if gcloud iam service-accounts describe "$SA_EMAIL" &>/dev/null; then
    echo "  Deleting service account: $SA_EMAIL"
    gcloud iam service-accounts delete "$SA_EMAIL" --quiet || true
else
    echo "  Service account $SA_EMAIL not found. Skipping."
fi

# -----------------------------------------------------------------------------
# 7. Delete local key file (if exists)
# -----------------------------------------------------------------------------
if [ -f "$SA_KEY_PATH" ]; then
    echo "  Deleting local key file: $SA_KEY_PATH"
    rm -f "$SA_KEY_PATH"
fi

# -----------------------------------------------------------------------------
# 8. Optional: Delete entire project
# -----------------------------------------------------------------------------
print_header "Cleanup Complete!"
echo ""
echo "All resources have been deleted."
echo ""
echo "Optional: To delete the entire project, run:"
echo "  gcloud projects delete $PROJECT_ID"
echo ""
echo "Note: Project deletion has a 30-day recovery period."
