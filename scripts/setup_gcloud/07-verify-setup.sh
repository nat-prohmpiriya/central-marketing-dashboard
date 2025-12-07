#!/bin/bash
# =============================================================================
# 07-verify-setup.sh - Verify GCP Setup
# =============================================================================
set -e

# Load environment
source "$(dirname "$0")/00-env.sh"

check_gcloud
print_header "Verifying GCP Setup"

# Set project
gcloud config set project "$PROJECT_ID"

ERRORS=0

# Check project
echo ""
echo "1. Checking project..."
if gcloud projects describe "$PROJECT_ID" &> /dev/null; then
    echo "   ✓ Project $PROJECT_ID exists"
else
    echo "   ✗ Project $PROJECT_ID not found"
    ((ERRORS++))
fi

# Check billing
echo ""
echo "2. Checking billing..."
BILLING=$(gcloud billing projects describe "$PROJECT_ID" --format="value(billingEnabled)" 2>/dev/null || echo "false")
if [ "$BILLING" = "True" ]; then
    echo "   ✓ Billing is enabled"
else
    echo "   ✗ Billing is NOT enabled"
    ((ERRORS++))
fi

# Check APIs
echo ""
echo "3. Checking APIs..."
REQUIRED_APIS=(
    "bigquery.googleapis.com"
    "cloudfunctions.googleapis.com"
    "cloudscheduler.googleapis.com"
    "secretmanager.googleapis.com"
    "storage.googleapis.com"
)
for api in "${REQUIRED_APIS[@]}"; do
    if gcloud services list --enabled --filter="name:$api" --format="value(name)" | grep -q "$api"; then
        echo "   ✓ $api"
    else
        echo "   ✗ $api NOT enabled"
        ((ERRORS++))
    fi
done

# Check service account
echo ""
echo "4. Checking service account..."
if gcloud iam service-accounts describe "$SA_EMAIL" &> /dev/null; then
    echo "   ✓ Service account $SA_EMAIL exists"
else
    echo "   ✗ Service account $SA_EMAIL not found"
    ((ERRORS++))
fi

# Check key file
echo ""
echo "5. Checking service account key..."
if [ -f "$SA_KEY_PATH" ]; then
    echo "   ✓ Key file exists at $SA_KEY_PATH"
else
    echo "   ✗ Key file not found at $SA_KEY_PATH"
    ((ERRORS++))
fi

# Check BigQuery datasets
echo ""
echo "6. Checking BigQuery datasets..."
for dataset in "$BQ_DATASET_RAW" "$BQ_DATASET_STAGING" "$BQ_DATASET_MART"; do
    if bq show "$PROJECT_ID:$dataset" &> /dev/null; then
        echo "   ✓ Dataset $dataset exists"
    else
        echo "   ✗ Dataset $dataset not found"
        ((ERRORS++))
    fi
done

# Check GCS bucket
echo ""
echo "7. Checking GCS bucket..."
if gsutil ls -b "gs://$GCS_BUCKET" &> /dev/null; then
    echo "   ✓ Bucket gs://$GCS_BUCKET exists"
else
    echo "   ✗ Bucket gs://$GCS_BUCKET not found"
    ((ERRORS++))
fi

# Check secrets
echo ""
echo "8. Checking Secret Manager secrets..."
SECRET_COUNT=$(gcloud secrets list --format="value(name)" | wc -l | tr -d ' ')
if [ "$SECRET_COUNT" -gt 0 ]; then
    echo "   ✓ $SECRET_COUNT secrets configured"
else
    echo "   ✗ No secrets found"
    ((ERRORS++))
fi

# Summary
print_header "Verification Complete"
if [ $ERRORS -eq 0 ]; then
    echo "✓ All checks passed!"
    echo ""
    echo "GCP setup is complete. You can now:"
    echo "  1. Add GOOGLE_APPLICATION_CREDENTIALS=$SA_KEY_PATH to .env"
    echo "  2. Update secrets with real API credentials"
    echo "  3. Proceed to Airbyte setup (1.1.3)"
    echo "  4. Or start building Base Classes (1.1.4)"
else
    echo "✗ $ERRORS check(s) failed!"
    echo ""
    echo "Please fix the issues above and re-run verification."
    exit 1
fi
