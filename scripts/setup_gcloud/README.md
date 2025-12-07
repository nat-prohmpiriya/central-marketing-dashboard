# GCP Setup Scripts

Scripts สำหรับ setup Google Cloud Platform resources.

## Prerequisites

1. ติดตั้ง [Google Cloud SDK](https://cloud.google.com/sdk/docs/install)
2. Login ด้วย `gcloud auth login`
3. สร้างหรือแก้ไขไฟล์ `.env` จาก `.env.example`

## Configuration

แก้ไขไฟล์ `.env` ที่ root ของ project:

```bash
# Required for GCP setup
GCP_PROJECT_ID=your-project-id
GCP_BILLING_ACCOUNT_ID=XXXXXX-XXXXXX-XXXXXX
GCP_REGION=asia-southeast1
```

หา Billing Account ID ได้จาก:
```bash
gcloud billing accounts list
```

## Usage

### Run ทีละ Step

```bash
cd scripts/setup_gcloud

# 1. Create project & link billing
./01-create-project.sh

# 2. Enable required APIs
./02-enable-apis.sh

# 3. Create service account & download key
./03-create-service-account.sh

# 4. Setup BigQuery datasets (raw, staging, mart)
./04-setup-bigquery.sh

# 5. Create secrets in Secret Manager
./05-setup-secret-manager.sh

# 6. Create GCS bucket for Airbyte staging
./06-create-gcs-bucket.sh

# 7. Verify all setup
./07-verify-setup.sh
```

### Run ทั้งหมด

```bash
cd scripts/setup_gcloud
./run-all.sh
```

## Scripts Overview

| Script | Task ID | Description |
|--------|---------|-------------|
| `00-env.sh` | - | Load environment variables (sourced by other scripts) |
| `01-create-project.sh` | G-001 | Create GCP project & enable billing |
| `02-enable-apis.sh` | G-002 | Enable BigQuery, Cloud Functions, etc. |
| `03-create-service-account.sh` | G-003 | Create service account & download key |
| `04-setup-bigquery.sh` | G-004 | Create datasets: raw, staging, mart |
| `05-setup-secret-manager.sh` | G-005 | Create placeholder secrets |
| `06-create-gcs-bucket.sh` | G-006 | Create GCS bucket for Airbyte |
| `07-verify-setup.sh` | - | Verify all resources created |
| `run-all.sh` | - | Run all scripts in sequence |

## After Setup

1. เพิ่มใน `.env`:
   ```
   GOOGLE_APPLICATION_CREDENTIALS=./secrets/etl-pipeline-sa-key.json
   ```

2. Update secrets ด้วย real values:
   ```bash
   echo -n 'your-real-value' | gcloud secrets versions add shopee-partner-id --data-file=-
   ```

3. ไปต่อที่ Airbyte setup หรือ Base Classes

## DEMO data

   ```bash 
   # Load ทั้งหมด 90 วัน
   uv run python scripts/demo_data/load_to_bigquery.py

   # Load แค่ 30 วัน
   uv run python scripts/demo_data/load_to_bigquery.py --days 30

   # Load เฉพาะ e-commerce
   uv run python scripts/demo_data/load_to_bigquery.py --type ecommerce
   ```
