#!/bin/bash
# =============================================================================
# 06-create-gcs-bucket.sh - Create GCS Staging Bucket (G-006)
# =============================================================================
set -e

# Load environment
source "$(dirname "$0")/00-env.sh"

check_gcloud
print_header "Step 6: Create GCS Staging Bucket"

# Set project
gcloud config set project "$PROJECT_ID"

echo "Bucket: gs://$GCS_BUCKET"
echo "Location: $LOCATION"
echo ""
confirm_proceed

# Check if bucket exists
if gsutil ls -b "gs://$GCS_BUCKET" &> /dev/null; then
    echo "Bucket gs://$GCS_BUCKET already exists. Skipping creation."
else
    echo "Creating bucket..."
    gsutil mb \
        -p "$PROJECT_ID" \
        -l "$LOCATION" \
        -c "STANDARD" \
        "gs://$GCS_BUCKET"
    echo "Bucket created."
fi

# Set lifecycle policy (delete objects after 30 days)
echo "Setting lifecycle policy (auto-delete after 30 days)..."
cat > /tmp/lifecycle.json << 'EOF'
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "Delete"},
        "condition": {"age": 30}
      }
    ]
  }
}
EOF
gsutil lifecycle set /tmp/lifecycle.json "gs://$GCS_BUCKET"
rm /tmp/lifecycle.json

# Grant service account access
echo "Granting service account access..."
gsutil iam ch "serviceAccount:$SA_EMAIL:roles/storage.objectAdmin" "gs://$GCS_BUCKET"

print_header "Step 6 Complete"
echo "GCS bucket created: gs://$GCS_BUCKET"
echo ""
echo "Bucket info:"
gsutil ls -L -b "gs://$GCS_BUCKET" | head -20
echo ""
echo "Next: Run 07-verify-setup.sh to verify all setup"
