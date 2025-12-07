#!/bin/bash
# =============================================================================
# 00-env.sh - Load environment variables for GCP setup
# =============================================================================
# This file is sourced by other setup scripts
# =============================================================================

# Load from .env file if exists
if [ -f "$(dirname "$0")/../../.env" ]; then
    export $(grep -v '^#' "$(dirname "$0")/../../.env" | xargs)
fi

# =============================================================================
# Required Variables - Set these before running setup scripts
# =============================================================================

# GCP Project
export PROJECT_ID="${GCP_PROJECT_ID:-central-marketing-dashboard}"
export PROJECT_NAME="${GCP_PROJECT_NAME:-Central Marketing Dashboard}"
export BILLING_ACCOUNT_ID="${GCP_BILLING_ACCOUNT_ID:-}"  # Required for new project

# Region & Location
export REGION="${GCP_REGION:-asia-southeast1}"
export LOCATION="${GCP_LOCATION:-asia-southeast1}"

# BigQuery Datasets
export BQ_DATASET_RAW="${BIGQUERY_DATASET_RAW:-raw}"
export BQ_DATASET_STAGING="${BIGQUERY_DATASET_STAGING:-staging}"
export BQ_DATASET_MART="${BIGQUERY_DATASET_MART:-mart}"

# Service Account
export SA_NAME="${GCP_SA_NAME:-etl-pipeline-sa}"
export SA_DISPLAY_NAME="${GCP_SA_DISPLAY_NAME:-ETL Pipeline Service Account}"

# Cloud Storage
export GCS_BUCKET="${GCS_STAGING_BUCKET:-${PROJECT_ID}-airbyte-staging}"

# =============================================================================
# Derived Variables (auto-generated)
# =============================================================================
export SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
export SA_KEY_PATH="${GCP_SA_KEY_PATH:-./secrets/${SA_NAME}-key.json}"

# =============================================================================
# Helper Functions
# =============================================================================

print_header() {
    echo ""
    echo "============================================================================="
    echo "$1"
    echo "============================================================================="
}

print_var() {
    echo "  $1: $2"
}

print_config() {
    print_header "Current Configuration"
    print_var "PROJECT_ID" "$PROJECT_ID"
    print_var "REGION" "$REGION"
    print_var "BQ_DATASET_RAW" "$BQ_DATASET_RAW"
    print_var "BQ_DATASET_STAGING" "$BQ_DATASET_STAGING"
    print_var "BQ_DATASET_MART" "$BQ_DATASET_MART"
    print_var "SA_NAME" "$SA_NAME"
    print_var "SA_EMAIL" "$SA_EMAIL"
    print_var "GCS_BUCKET" "$GCS_BUCKET"
    echo ""
}

check_gcloud() {
    if ! command -v gcloud &> /dev/null; then
        echo "ERROR: gcloud CLI not found. Please install Google Cloud SDK."
        echo "https://cloud.google.com/sdk/docs/install"
        exit 1
    fi
}

confirm_proceed() {
    read -p "Proceed? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 1
    fi
}
