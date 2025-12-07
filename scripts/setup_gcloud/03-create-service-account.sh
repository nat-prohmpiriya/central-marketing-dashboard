#!/bin/bash
# =============================================================================
# 03-create-service-account.sh - Create Service Account (G-003)
# =============================================================================
set -e

# Load environment
source "$(dirname "$0")/00-env.sh"

check_gcloud
print_header "Step 3: Create Service Account"

# Set project
gcloud config set project "$PROJECT_ID"

echo "Service Account: $SA_NAME"
echo "Email: $SA_EMAIL"
echo "Key Path: $SA_KEY_PATH"
echo ""
confirm_proceed

# Check if service account exists
if gcloud iam service-accounts describe "$SA_EMAIL" &> /dev/null; then
    echo "Service account $SA_EMAIL already exists. Skipping creation."
else
    echo "Creating service account..."
    gcloud iam service-accounts create "$SA_NAME" \
        --display-name="$SA_DISPLAY_NAME" \
        --description="Service account for ETL pipeline operations"
    echo "Service account created."
fi

# Assign roles
echo "Assigning IAM roles..."

ROLES=(
    "roles/bigquery.admin"                 # BigQuery Admin
    "roles/storage.admin"                  # Storage Admin
    "roles/secretmanager.secretAccessor"   # Secret Manager Accessor
    "roles/cloudfunctions.invoker"         # Cloud Functions Invoker
    "roles/logging.logWriter"              # Log Writer
)

for role in "${ROLES[@]}"; do
    echo "  Assigning $role..."
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
        --member="serviceAccount:$SA_EMAIL" \
        --role="$role" \
        --quiet
done

# Create key directory
KEY_DIR=$(dirname "$SA_KEY_PATH")
mkdir -p "$KEY_DIR"

# Generate JSON key
if [ -f "$SA_KEY_PATH" ]; then
    echo ""
    echo "WARNING: Key file already exists at $SA_KEY_PATH"
    read -p "Overwrite? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Skipping key generation."
    else
        rm "$SA_KEY_PATH"
        gcloud iam service-accounts keys create "$SA_KEY_PATH" \
            --iam-account="$SA_EMAIL"
        echo "New key created."
    fi
else
    echo "Creating service account key..."
    gcloud iam service-accounts keys create "$SA_KEY_PATH" \
        --iam-account="$SA_EMAIL"
    echo "Key created at $SA_KEY_PATH"
fi

# Set permissions on key file
chmod 600 "$SA_KEY_PATH"

print_header "Step 3 Complete"
echo "Service account created with roles:"
for role in "${ROLES[@]}"; do
    echo "  - $role"
done
echo ""
echo "Key saved to: $SA_KEY_PATH"
echo ""
echo "IMPORTANT: Add to .env:"
echo "  GOOGLE_APPLICATION_CREDENTIALS=$SA_KEY_PATH"
echo ""
echo "Next: Run 04-setup-bigquery.sh"


#   | Service         | ฟรี                             | เสียเงินเมื่อ|
#   |-----------------|---------------------------------|---------------------|
#   | BigQuery        | 10 GB storage, 1 TB query/เดือน | เกิน free tier|
#   | Cloud Functions | 2 ล้าน invocations/เดือน        | เกิน free tier|
#   | Cloud Scheduler | 3 jobs ฟรี                      | job ที่ 4+|
#   | Secret Manager  | 6 secrets ฟรี                   | เกิน + access calls |
#   | Cloud Storage   | 5 GB ฟรี                        | เกิน free tier|
#   | Logging         | 50 GB/เดือน ฟรี                 | เกิน free tier