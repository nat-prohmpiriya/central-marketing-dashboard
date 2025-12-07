#!/bin/bash
# =============================================================================
# 05-setup-secret-manager.sh - Setup Secret Manager (G-005)
# =============================================================================
set -e

# Load environment
source "$(dirname "$0")/00-env.sh"

check_gcloud
print_header "Step 5: Setup Secret Manager"

# Set project
gcloud config set project "$PROJECT_ID"

# List of secrets to create (empty placeholders)
SECRETS=(
    "shopee-partner-id"
    "shopee-partner-key"
    "shopee-shop-id"
    "shopee-access-token"
    "shopee-refresh-token"
    "lazada-app-key"
    "lazada-app-secret"
    "lazada-access-token"
    "lazada-refresh-token"
    "tiktok-shop-app-key"
    "tiktok-shop-app-secret"
    "tiktok-shop-access-token"
    "line-ads-access-token"
)

echo "Will create the following secrets in project $PROJECT_ID:"
for secret in "${SECRETS[@]}"; do
    echo "  - $secret"
done
echo ""
echo "Note: Secrets will be created with placeholder values."
echo "You'll need to update them with real values later."
echo ""
confirm_proceed

# Create secrets
create_secret() {
    local secret_name=$1

    if gcloud secrets describe "$secret_name" &> /dev/null; then
        echo "Secret $secret_name already exists. Skipping."
    else
        echo "Creating secret $secret_name..."
        # Create secret
        gcloud secrets create "$secret_name" \
            --replication-policy="user-managed" \
            --locations="$REGION"

        # Add placeholder version
        echo -n "REPLACE_WITH_REAL_VALUE" | \
            gcloud secrets versions add "$secret_name" --data-file=-

        echo "Secret $secret_name created."
    fi
}

for secret in "${SECRETS[@]}"; do
    create_secret "$secret"
done

# Grant service account access
echo ""
echo "Granting service account access to secrets..."
for secret in "${SECRETS[@]}"; do
    gcloud secrets add-iam-policy-binding "$secret" \
        --member="serviceAccount:$SA_EMAIL" \
        --role="roles/secretmanager.secretAccessor" \
        --quiet
done

print_header "Step 5 Complete"
echo "Secrets created (with placeholder values):"
gcloud secrets list
echo ""
echo "To update a secret value:"
echo "  echo -n 'your-value' | gcloud secrets versions add SECRET_NAME --data-file=-"
echo ""
echo "Next: Run 06-create-gcs-bucket.sh"
