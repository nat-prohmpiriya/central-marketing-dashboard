#!/bin/bash
# =============================================================================
# 01-create-project.sh - Create GCP Project (G-001)
# =============================================================================
set -e

# Load environment
source "$(dirname "$0")/00-env.sh"

check_gcloud
print_header "Step 1: Create GCP Project"
print_config

# Check if billing account is set
if [ -z "$BILLING_ACCOUNT_ID" ]; then
    echo "Available billing accounts:"
    gcloud billing accounts list
    echo ""
    echo "ERROR: BILLING_ACCOUNT_ID is not set."
    echo "Set it in .env or export GCP_BILLING_ACCOUNT_ID=<your-billing-account-id>"
    exit 1
fi

echo "Will create project: $PROJECT_ID"
echo "Billing account: $BILLING_ACCOUNT_ID"
confirm_proceed

# Check if project already exists
if gcloud projects describe "$PROJECT_ID" &> /dev/null; then
    echo "Project $PROJECT_ID already exists. Skipping creation."
else
    echo "Creating project..."
    gcloud projects create "$PROJECT_ID" --name="$PROJECT_NAME"
    echo "Project created successfully."
fi

# Link billing account
echo "Linking billing account..."
gcloud billing projects link "$PROJECT_ID" --billing-account="$BILLING_ACCOUNT_ID"

# Set as default project
echo "Setting as default project..."
gcloud config set project "$PROJECT_ID"

print_header "Step 1 Complete"
echo "Project $PROJECT_ID created and billing enabled."
echo ""
echo "Next: Run 02-enable-apis.sh"
