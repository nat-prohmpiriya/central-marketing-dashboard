#!/bin/bash
# =============================================================================
# 04-setup-bigquery.sh - Setup BigQuery Datasets (G-004)
# =============================================================================
set -e

# Load environment
source "$(dirname "$0")/00-env.sh"

check_gcloud
print_header "Step 4: Setup BigQuery Datasets"

# Set project
gcloud config set project "$PROJECT_ID"

echo "Will create datasets in project $PROJECT_ID:"
echo "  - $BQ_DATASET_RAW"
echo "  - $BQ_DATASET_STAGING"
echo "  - $BQ_DATASET_MART"
echo "Location: $LOCATION"
echo ""
confirm_proceed

# Create datasets
create_dataset() {
    local dataset=$1
    local description=$2

    if bq show "$PROJECT_ID:$dataset" &> /dev/null; then
        echo "Dataset $dataset already exists. Skipping."
    else
        echo "Creating dataset $dataset..."
        bq mk \
            --dataset \
            --location="$LOCATION" \
            --description="$description" \
            "$PROJECT_ID:$dataset"
        echo "Dataset $dataset created."
    fi
}

create_dataset "$BQ_DATASET_RAW" "Raw layer - ingested data from sources"
create_dataset "$BQ_DATASET_STAGING" "Staging layer - cleaned and normalized data"
create_dataset "$BQ_DATASET_MART" "Mart layer - aggregated data for dashboards"

# Grant service account access
echo ""
echo "Granting service account access to datasets..."
for dataset in "$BQ_DATASET_RAW" "$BQ_DATASET_STAGING" "$BQ_DATASET_MART"; do
    echo "  Setting permissions for $dataset..."
    # Get current policy, add service account, update
    bq show --format=json "$PROJECT_ID:$dataset" | \
        jq ".access += [{\"role\": \"WRITER\", \"userByEmail\": \"$SA_EMAIL\"}]" | \
        bq update --source /dev/stdin "$PROJECT_ID:$dataset" 2>/dev/null || true
done

print_header "Step 4 Complete"
echo "BigQuery datasets created:"
bq ls --project_id="$PROJECT_ID"
echo ""
echo "Next: Run 05-setup-secret-manager.sh"

#   | Dataset | ใช้เก็บอะไร                                        |
#   |---------|----------------------------------------------------|
#   | raw     | ข้อมูลดิบจาก APIs (Shopee, Lazada, Facebook, etc.) |
#   | staging | ข้อมูลที่ transform แล้ว                           |
#   | mart    | ข้อมูลพร้อมใช้ใน Dashboard                         