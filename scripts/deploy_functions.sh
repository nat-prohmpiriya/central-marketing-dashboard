#!/bin/bash
# Deploy script for Cloud Functions
# Usage: ./scripts/deploy_functions.sh [function_name]
#
# Examples:
#   ./scripts/deploy_functions.sh           # Deploy all functions
#   ./scripts/deploy_functions.sh ecommerce # Deploy only ecommerce function
#   ./scripts/deploy_functions.sh ads       # Deploy only ads function
#   ./scripts/deploy_functions.sh mart      # Deploy only mart function
#   ./scripts/deploy_functions.sh alerts    # Deploy only alerts function

set -e

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-your-project-id}"
REGION="${GCP_REGION:-asia-southeast1}"
RUNTIME="python311"
MEMORY="512MB"
TIMEOUT="540s"
SERVICE_ACCOUNT="${GCP_SERVICE_ACCOUNT:-}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CLOUD_FUNCTIONS_DIR="$PROJECT_ROOT/cloud_functions"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Cloud Functions Deployment Script    ${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Project ID: $PROJECT_ID"
echo "Region: $REGION"
echo "Runtime: $RUNTIME"
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}Error: gcloud CLI is not installed${NC}"
    exit 1
fi

# Function to deploy a single Cloud Function
deploy_function() {
    local function_name=$1
    local entry_point=$2
    local source_dir=$3
    local description=$4
    local extra_args=$5

    echo -e "${YELLOW}Deploying: $function_name${NC}"
    echo "  Source: $source_dir"
    echo "  Entry point: $entry_point"
    echo ""

    # Build command
    local cmd="gcloud functions deploy $function_name \
        --gen2 \
        --runtime=$RUNTIME \
        --region=$REGION \
        --source=$source_dir \
        --entry-point=$entry_point \
        --trigger-http \
        --allow-unauthenticated \
        --memory=$MEMORY \
        --timeout=$TIMEOUT \
        --project=$PROJECT_ID"

    # Add service account if specified
    if [ -n "$SERVICE_ACCOUNT" ]; then
        cmd="$cmd --service-account=$SERVICE_ACCOUNT"
    fi

    # Add extra args
    if [ -n "$extra_args" ]; then
        cmd="$cmd $extra_args"
    fi

    # Execute deployment
    if eval $cmd; then
        echo -e "${GREEN}✓ Successfully deployed: $function_name${NC}"
        echo ""
    else
        echo -e "${RED}✗ Failed to deploy: $function_name${NC}"
        return 1
    fi
}

# Deploy E-commerce ETL Function
deploy_ecommerce() {
    # Copy source files
    echo "Preparing source for etl-ecommerce..."
    cp -r "$PROJECT_ROOT/src" "$CLOUD_FUNCTIONS_DIR/etl_ecommerce/"

    deploy_function \
        "etl-ecommerce" \
        "etl_ecommerce" \
        "$CLOUD_FUNCTIONS_DIR/etl_ecommerce" \
        "E-commerce ETL pipeline (Shopee, Lazada, TikTok Shop)"

    # Cleanup
    rm -rf "$CLOUD_FUNCTIONS_DIR/etl_ecommerce/src"
}

# Deploy Ads ETL Function
deploy_ads() {
    # Copy source files
    echo "Preparing source for etl-ads..."
    cp -r "$PROJECT_ROOT/src" "$CLOUD_FUNCTIONS_DIR/etl_ads/"

    deploy_function \
        "etl-ads" \
        "etl_ads" \
        "$CLOUD_FUNCTIONS_DIR/etl_ads" \
        "Ads ETL pipeline (Facebook, Google, TikTok, LINE, Shopee, Lazada, GA4)" \
        "--memory=1024MB"

    # Cleanup
    rm -rf "$CLOUD_FUNCTIONS_DIR/etl_ads/src"
}

# Deploy Mart ETL Function
deploy_mart() {
    # Copy source files
    echo "Preparing source for etl-mart..."
    cp -r "$PROJECT_ROOT/src" "$CLOUD_FUNCTIONS_DIR/etl_mart/"
    cp -r "$PROJECT_ROOT/sql" "$CLOUD_FUNCTIONS_DIR/etl_mart/"

    deploy_function \
        "etl-mart" \
        "etl_mart" \
        "$CLOUD_FUNCTIONS_DIR/etl_mart" \
        "Mart refresh pipeline (BigQuery transformations)" \
        "--memory=1024MB"

    # Cleanup
    rm -rf "$CLOUD_FUNCTIONS_DIR/etl_mart/src"
    rm -rf "$CLOUD_FUNCTIONS_DIR/etl_mart/sql"
}

# Deploy Alerts ETL Function
deploy_alerts() {
    # Copy source files
    echo "Preparing source for etl-alerts..."
    cp -r "$PROJECT_ROOT/src" "$CLOUD_FUNCTIONS_DIR/etl_alerts/"
    cp -r "$PROJECT_ROOT/sql" "$CLOUD_FUNCTIONS_DIR/etl_alerts/"

    deploy_function \
        "etl-alerts" \
        "etl_alerts" \
        "$CLOUD_FUNCTIONS_DIR/etl_alerts" \
        "Alerts generation pipeline (rule-based marketing alerts)"

    # Cleanup
    rm -rf "$CLOUD_FUNCTIONS_DIR/etl_alerts/src"
    rm -rf "$CLOUD_FUNCTIONS_DIR/etl_alerts/sql"
}

# Deploy Get Alerts Function (read-only endpoint)
deploy_get_alerts() {
    # Copy source files
    echo "Preparing source for get-alerts..."
    cp -r "$PROJECT_ROOT/src" "$CLOUD_FUNCTIONS_DIR/etl_alerts/"
    cp -r "$PROJECT_ROOT/sql" "$CLOUD_FUNCTIONS_DIR/etl_alerts/"

    deploy_function \
        "get-alerts" \
        "get_alerts" \
        "$CLOUD_FUNCTIONS_DIR/etl_alerts" \
        "Get active marketing alerts (read-only endpoint)" \
        "--memory=256MB"

    # Cleanup
    rm -rf "$CLOUD_FUNCTIONS_DIR/etl_alerts/src"
    rm -rf "$CLOUD_FUNCTIONS_DIR/etl_alerts/sql"
}

# Deploy all functions
deploy_all() {
    echo -e "${GREEN}Deploying all Cloud Functions...${NC}"
    echo ""

    local failed=0

    deploy_ecommerce || ((failed++))
    deploy_ads || ((failed++))
    deploy_mart || ((failed++))
    deploy_alerts || ((failed++))
    deploy_get_alerts || ((failed++))

    echo ""
    if [ $failed -eq 0 ]; then
        echo -e "${GREEN}========================================${NC}"
        echo -e "${GREEN}  All functions deployed successfully!  ${NC}"
        echo -e "${GREEN}========================================${NC}"
    else
        echo -e "${RED}========================================${NC}"
        echo -e "${RED}  $failed function(s) failed to deploy  ${NC}"
        echo -e "${RED}========================================${NC}"
        exit 1
    fi
}

# Create Cloud Scheduler jobs
create_schedulers() {
    echo -e "${YELLOW}Creating Cloud Scheduler jobs...${NC}"
    echo ""

    # Get function URLs
    ECOMMERCE_URL=$(gcloud functions describe etl-ecommerce --gen2 --region=$REGION --format='value(serviceConfig.uri)' 2>/dev/null || echo "")
    ADS_URL=$(gcloud functions describe etl-ads --gen2 --region=$REGION --format='value(serviceConfig.uri)' 2>/dev/null || echo "")
    MART_URL=$(gcloud functions describe etl-mart --gen2 --region=$REGION --format='value(serviceConfig.uri)' 2>/dev/null || echo "")
    ALERTS_URL=$(gcloud functions describe etl-alerts --gen2 --region=$REGION --format='value(serviceConfig.uri)' 2>/dev/null || echo "")

    if [ -z "$ECOMMERCE_URL" ] || [ -z "$ADS_URL" ] || [ -z "$MART_URL" ] || [ -z "$ALERTS_URL" ]; then
        echo -e "${RED}Error: Functions not deployed. Deploy functions first.${NC}"
        exit 1
    fi

    # E-commerce scheduler (every 6 hours)
    echo "Creating etl-ecommerce-scheduler..."
    gcloud scheduler jobs create http etl-ecommerce-scheduler \
        --location=$REGION \
        --schedule="0 */6 * * *" \
        --time-zone="Asia/Bangkok" \
        --uri="$ECOMMERCE_URL" \
        --http-method=POST \
        --message-body='{"days_back": 7, "platforms": ["shopee", "lazada", "tiktok_shop"]}' \
        --headers="Content-Type=application/json" \
        --project=$PROJECT_ID \
        --quiet || echo "Scheduler may already exist"

    # Ads scheduler (every 6 hours, offset by 30 minutes)
    echo "Creating etl-ads-scheduler..."
    gcloud scheduler jobs create http etl-ads-scheduler \
        --location=$REGION \
        --schedule="30 */6 * * *" \
        --time-zone="Asia/Bangkok" \
        --uri="$ADS_URL" \
        --http-method=POST \
        --message-body='{"days_back": 7, "include_ga4": true}' \
        --headers="Content-Type=application/json" \
        --project=$PROJECT_ID \
        --quiet || echo "Scheduler may already exist"

    # Mart scheduler (1 hour after ETL)
    echo "Creating etl-mart-scheduler..."
    gcloud scheduler jobs create http etl-mart-scheduler \
        --location=$REGION \
        --schedule="0 1,7,13,19 * * *" \
        --time-zone="Asia/Bangkok" \
        --uri="$MART_URL" \
        --http-method=POST \
        --message-body='{"parallel": false}' \
        --headers="Content-Type=application/json" \
        --project=$PROJECT_ID \
        --quiet || echo "Scheduler may already exist"

    # Alerts scheduler (daily at 7 AM)
    echo "Creating etl-alerts-scheduler..."
    gcloud scheduler jobs create http etl-alerts-scheduler \
        --location=$REGION \
        --schedule="0 7 * * *" \
        --time-zone="Asia/Bangkok" \
        --uri="$ALERTS_URL" \
        --http-method=POST \
        --message-body='{"run_sql": true}' \
        --headers="Content-Type=application/json" \
        --project=$PROJECT_ID \
        --quiet || echo "Scheduler may already exist"

    echo -e "${GREEN}Cloud Scheduler jobs created!${NC}"
}

# List deployed functions
list_functions() {
    echo -e "${YELLOW}Deployed Cloud Functions:${NC}"
    gcloud functions list --gen2 --region=$REGION --project=$PROJECT_ID
}

# Print usage
print_usage() {
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  all         Deploy all functions (default)"
    echo "  ecommerce   Deploy E-commerce ETL function"
    echo "  ads         Deploy Ads ETL function"
    echo "  mart        Deploy Mart ETL function"
    echo "  alerts      Deploy Alerts ETL function"
    echo "  schedulers  Create Cloud Scheduler jobs"
    echo "  list        List deployed functions"
    echo "  help        Show this help message"
    echo ""
    echo "Environment variables:"
    echo "  GCP_PROJECT_ID      GCP project ID (required)"
    echo "  GCP_REGION          GCP region (default: asia-southeast1)"
    echo "  GCP_SERVICE_ACCOUNT Service account email (optional)"
}

# Main
case "${1:-all}" in
    all)
        deploy_all
        ;;
    ecommerce)
        deploy_ecommerce
        ;;
    ads)
        deploy_ads
        ;;
    mart)
        deploy_mart
        ;;
    alerts)
        deploy_alerts
        ;;
    schedulers)
        create_schedulers
        ;;
    list)
        list_functions
        ;;
    help|--help|-h)
        print_usage
        ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        print_usage
        exit 1
        ;;
esac
