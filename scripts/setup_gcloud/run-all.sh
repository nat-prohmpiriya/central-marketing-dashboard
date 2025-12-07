#!/bin/bash
# =============================================================================
# run-all.sh - Run all GCP setup scripts in sequence
# =============================================================================
set -e

SCRIPT_DIR="$(dirname "$0")"

echo "============================================================================="
echo "Central Marketing Dashboard - GCP Setup"
echo "============================================================================="
echo ""
echo "This will run all setup scripts in sequence:"
echo "  01. Create GCP Project"
echo "  02. Enable APIs"
echo "  03. Create Service Account"
echo "  04. Setup BigQuery Datasets"
echo "  05. Setup Secret Manager"
echo "  06. Create GCS Bucket"
echo "  07. Verify Setup"
echo ""
read -p "Continue? (y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

# Run scripts in order
"$SCRIPT_DIR/01-create-project.sh"
"$SCRIPT_DIR/02-enable-apis.sh"
"$SCRIPT_DIR/03-create-service-account.sh"
"$SCRIPT_DIR/04-setup-bigquery.sh"
"$SCRIPT_DIR/05-setup-secret-manager.sh"
"$SCRIPT_DIR/06-create-gcs-bucket.sh"
"$SCRIPT_DIR/07-verify-setup.sh"

echo ""
echo "============================================================================="
echo "All GCP setup complete!"
echo "============================================================================="
