# Risks & Limitations: Python Extractors

## Overview

**Document Type:** Risk Assessment & Technical Limitations
**Phase:** Phase 1 - Single Tenant MVP
**Last Updated:** December 2025

### Reference Documents
- Product Specification: `.docs/01-spec.md`
- Technical Plan: `.docs/02-plan.md`
- Development Tasks: `.docs/03-tasks.md`

---

## Executive Summary

โปรเจกต์นี้ใช้ **Hybrid ETL Approach**:
- **Airbyte (4 platforms):** Facebook Ads, Google Ads, GA4, TikTok Ads - มี official connectors พร้อมใช้
- **Python Custom (6 platforms):** Shopee, Lazada, TikTok Shop, LINE Ads, Shopee Ads, Lazada Ads - ต้องพัฒนาเอง

เอกสารนี้รวบรวมข้อควรระวัง อุปสรรค และแนวทางแก้ไขสำหรับ platforms ที่ต้องพัฒนา Python extractors เอง

---

## 1. Shopee (Orders/Products)

### 1.1 API Access Requirements

| ประเด็น | รายละเอียด | ความเสี่ยง |
|---------|------------|-----------|
| **Managed Seller Only** | Thailand: OpenAPI ให้เฉพาะ Managed Sellers (มี Key Account Manager ดูแล) เท่านั้น | 🔴 High |
| **Alternative** | ถ้าไม่ใช่ Managed Seller ต้องใช้ Third-party Partner Platform | 🟡 Medium |

### 1.2 Technical Limitations

| ประเด็น | รายละเอียด | แนวทางแก้ไข |
|---------|------------|-------------|
| **Rate Limit** | ~100 requests/minute/account | Implement exponential backoff, request queue |
| **Token Expiry** | Access token หมดอายุ ต้อง refresh | Auto-refresh mechanism ใน BaseExtractor |
| **Historical Data** | API ให้ข้อมูลย้อนหลังแค่ ~30 วัน | Sync ทุกวันเพื่อ accumulate data ใน BigQuery |
| **Pagination** | ต้อง handle pagination สำหรับ large datasets | Cursor-based pagination logic |

### 1.3 Pre-requisites Checklist

- [ ] ยืนยันว่าลูกค้าเป็น Shopee Managed Seller
- [ ] มี Shopee Partner ID และ Partner Key
- [ ] มี Shop ID สำหรับทุกร้านที่ต้องการเชื่อม
- [ ] ลูกค้า authorize app ผ่าน OAuth flow

### 1.4 References
- [Shopee Open Platform](https://open.shopee.com/)
- [Shopee API Essentials](https://rollout.com/integration-guides/shopee/api-essentials)
- [Shopee Thailand Developer Guide](https://seller.shopee.co.th/edu/article/15124)

---

## 2. Lazada (Orders/Products)

### 2.1 API Access Requirements

| ประเด็น | รายละเอียด | ความเสี่ยง |
|---------|------------|-----------|
| **Developer Approval** | ต้องขอ approval จาก Lazada Open Platform | 🟢 Low |
| **Category Approval** | แต่ละ category (Orders, Products, etc.) ต้อง approve แยก | 🟡 Medium |
| **Active Profile** | Developer profile ต้อง active | 🟢 Low |

### 2.2 Technical Limitations

| ประเด็น | รายละเอียด | แนวทางแก้ไข |
|---------|------------|-------------|
| **Signature Generation** | ต้อง generate signature ถูกต้องตาม algorithm | ใช้ official SDK หรือ verified library |
| **Multi-region Endpoints** | แต่ละ region (TH, MY, SG) endpoint ต่างกัน | Config per-region ใน platforms.yaml |
| **API Changes** | เคยมี API migration (Seller Center → Open Platform) | Monitor announcements, version lock |
| **OAuth 2.0** | Authentication ใช้ OAuth 2.0 | Implement proper token flow |

### 2.3 Pre-requisites Checklist

- [ ] สมัคร Lazada Open Platform developer account
- [ ] Submit app สำหรับ review
- [ ] ได้รับ App Key และ App Secret
- [ ] Request API permissions ที่ต้องการ
- [ ] ลูกค้า authorize app

### 2.4 References
- [Lazada Open Platform](https://open.lazada.com/)
- [Lazada API Documentation](https://open.lazada.com/apps/doc/doc?nodeId=10534&docId=108130)
- [Lazada Integration Guide](https://api2cart.com/api-technology/lazada-integration-how-to-develop-it-easily/)

---

## 3. TikTok Shop (Orders/Products)

### 3.1 API Access Requirements

| ประเด็น | รายละเอียด | ความเสี่ยง |
|---------|------------|-----------|
| **Approval Delays** | ต้องมี working prototype + รอ 5-7 วัน | 🟡 Medium |
| **Permission Review** | ต้องเขียน summary ว่าจะใช้ permission อย่างไร | 🟡 Medium |
| **Feedback Loop** | อาจได้รับ feedback ให้แก้ไขและ resubmit | 🟡 Medium |

### 3.2 Technical Limitations

| ประเด็น | รายละเอียด | แนวทางแก้ไข |
|---------|------------|-------------|
| **Rate Limit** | HTTP 429 เมื่อเกิน limit (per-minute sliding window) | Retry with exponential backoff |
| **Token Management** | Access token security และ expiry | Secure storage (Secret Manager) + auto-refresh |
| **Signature Algorithm** | เคยเป็น pain point สำหรับ developers | ดู updated documentation |
| **Limited Historical** | อาจมีข้อจำกัดเรื่องข้อมูลย้อนหลัง | Sync บ่อยๆ เพื่อ accumulate |

### 3.3 Recent Improvements (2025)

TikTok ได้ปรับปรุง developer experience:
- Refreshed documentation สำหรับ authorization และ signature
- Step-by-step instructions สำหรับ first API call
- Glossary of common error codes
- Widgets ใช้ได้โดยไม่ต้อง request access

### 3.4 Pre-requisites Checklist

- [ ] สมัคร TikTok Shop Partner Center account
- [ ] เตรียม working prototype/mockup
- [ ] เขียน permission usage summary
- [ ] Submit และรอ approval (5-7 days)
- [ ] ลูกค้า authorize shop

### 3.5 References
- [TikTok Shop Partner Center](https://partner.tiktokshop.com/)
- [TikTok Developer Updates](https://developers.tiktok.com/blog/tiktok-shop-developer-updates)
- [TikTok API Integration Guide](https://api2cart.com/api-technology/tiktok-api/)

---

## 4. LINE Ads

### 4.1 API Access Requirements

| ประเด็น | รายละเอียด | ความเสี่ยง |
|---------|------------|-----------|
| **Public API Availability** | ไม่แน่ใจว่ามี public API สำหรับ Ads reporting | 🔴 High |
| **LINE OA Required** | อาจต้องเชื่อมผ่าน LINE Official Account | 🟡 Medium |
| **Thailand Focus** | Platform focus เฉพาะ Thailand/Asia | 🟢 Low (ข้อดี) |

### 4.2 Technical Limitations

| ประเด็น | รายละเอียด | แนวทางแก้ไข |
|---------|------------|-------------|
| **Documentation** | Documentation อาจไม่ครบถ้วน | ติดต่อ LINE Business Thailand โดยตรง |
| **No Public API** | อาจไม่มี public API | **Alternative: Manual CSV export** |
| **LINE OA Integration** | อาจต้องใช้ LINE Official Account API | ตรวจสอบ requirements |

### 4.3 Alternative Approaches

1. **CSV Export (Recommended)**
   - Export รายงานจาก LINE Ads Manager manually
   - Upload CSV ไปยัง GCS → BigQuery
   - Schedule: Weekly หรือ Monthly

2. **LINE Official Account API**
   - ถ้าต้องการ integration มากขึ้น
   - ต้องมี LINE Official Account ของธุรกิจ

3. **Contact LINE Business Thailand**
   - สอบถาม API access สำหรับ Ads reporting
   - อาจมี enterprise solution

### 4.4 Pre-requisites Checklist

- [ ] ตรวจสอบว่าลูกค้าใช้ LINE Ads หรือไม่
- [ ] ถ้าใช้ ตรวจสอบว่ามี LINE Official Account หรือไม่
- [ ] ติดต่อ LINE Business Thailand สอบถาม API
- [ ] ถ้าไม่มี API → ใช้ CSV export approach

### 4.5 References
- [LINE Developers](https://developers.line.biz/)
- [LINE for Business Thailand](https://lineforbusiness.com/th/)
- [LINE Ads Manager](https://admanager.line.biz/)

---

## 5. Shopee Ads

### 5.1 API Access Requirements

| ประเด็น | รายละเอียด | ความเสี่ยง |
|---------|------------|-----------|
| **No Public API** | Shopee Ads ไม่มี public API แยกต่างหาก | 🔴 High |
| **Dashboard Only** | Ads management ทำผ่าน Shopee Seller Center UI เท่านั้น | 🔴 High |
| **Off-Platform Ads** | Shopee Off-Platform Ads (Facebook/IG) อาจดึงจาก Facebook API | 🟡 Medium |

### 5.2 Technical Limitations

| ประเด็น | รายละเอียด | แนวทางแก้ไข |
|---------|------------|-------------|
| **No API** | ไม่สามารถดึงข้อมูลผ่าน API | **Alternative: Manual CSV export** |
| **Manual Process** | ต้อง export จาก Seller Center | Schedule weekly export |
| **Data Freshness** | ข้อมูลอาจไม่ real-time | Accept delay |

### 5.3 Alternative Approaches

1. **CSV Export (Recommended)**
   - Export รายงาน Shopee Ads จาก Seller Center
   - Upload CSV ไปยัง GCS → BigQuery
   - Schedule: Weekly

2. **Shopee Off-Platform Ads via Facebook**
   - ถ้าใช้ Shopee Off-Platform Ads (Facebook/IG integration)
   - ข้อมูลอาจดึงได้จาก Facebook Ads API (ผ่าน Airbyte)

3. **Future API**
   - Monitor Shopee announcements สำหรับ Ads API ในอนาคต

### 5.4 Pre-requisites Checklist

- [ ] ตรวจสอบว่าลูกค้าใช้ Shopee Ads หรือไม่
- [ ] ถ้าใช้ ตรวจสอบว่าใช้ In-Platform หรือ Off-Platform Ads
- [ ] ถ้า Off-Platform → ดึงจาก Facebook Ads API
- [ ] ถ้า In-Platform → ใช้ CSV export approach

### 5.5 References
- [Shopee Seller Center](https://seller.shopee.co.th/)
- [Shopee Ads Guide](https://seller.shopee.co.th/edu/category/20)

---

## 6. Lazada Ads (Sponsored Solutions)

### 6.1 API Access Requirements

| ประเด็น | รายละเอียด | ความเสี่ยง |
|---------|------------|-----------|
| **API Available** | Lazada Sponsored Solutions มี Open API | 🟢 Low |
| **Developer Registration** | ต้องสมัคร UAC account + register app + รอ review | 🟡 Medium |
| **Phase 1 Scope** | API Phase 1 รองรับ Sponsored Discovery เป็นหลัก | 🟡 Medium |

### 6.2 Technical Limitations

| ประเด็น | รายละเอียด | แนวทางแก้ไข |
|---------|------------|-------------|
| **Limited Scope** | Phase 1 อาจไม่ครอบคลุม Sponsored Affiliate/Display | ตรวจสอบ scope ที่ต้องการ |
| **Target Users** | เหมาะกับ big brands ที่มี multiple accounts | อาจ overkill สำหรับ small sellers |
| **UAC Account** | ต้องมี Unified Account Center account | สมัครก่อน |

### 6.3 API Capabilities

Lazada Sponsored Solutions API รองรับ:
- Manage accounts at granular level (customers, keywords)
- Automate tasks (filter low-efficiency creatives, replace them)
- Cross-store และ multi-dimensional data analysis
- Batch operations (create, pause, enable, adjust bids)
- Excel import/export

### 6.4 Pre-requisites Checklist

- [ ] สมัคร Lazada UAC (Unified Account Center) account
- [ ] Sign up as Lazada developer
- [ ] Register application และ submit for review
- [ ] ได้รับ App Key และ App Secret
- [ ] Request Sponsored Solutions API permission

### 6.5 References
- [Lazada Sponsored Solutions](https://www.lazadasolutions.com/)
- [LSS API Announcement](https://open.lazada.com/apps/announcement/detail?docId=1816)
- [LSS API Introduction](https://open.alitrip.com/docs/doc.htm?treeId=499&articleId=121250&docType=1)

---

## Risk Assessment Matrix

### Overall Risk by Platform

| Platform | API Available | Difficulty | Risk Level | Priority |
|----------|---------------|------------|------------|----------|
| **Shopee** | ✅ Yes (Managed Sellers) | 🟡 Medium | 🟡 **Medium** | 🥇 High |
| **Lazada** | ✅ Yes | 🟡 Medium | 🟢 **Low** | 🥇 High |
| **TikTok Shop** | ✅ Yes | 🟠 Medium-High | 🟡 **Medium** | 🥇 High |
| **LINE Ads** | ❓ Unknown | 🔴 High | 🔴 **High** | 🥉 Low |
| **Shopee Ads** | ❌ No | 🔴 High | 🔴 **High** | 🥉 Low |
| **Lazada Ads** | ✅ Yes | 🟡 Medium | 🟢 **Low** | 🥈 Medium |

### Risk Categories

#### 🟢 Low Risk (Ready to implement)
- **Lazada Orders/Products** - API พร้อม, approval process ไม่ยาก
- **Lazada Ads (LSS)** - มี API พร้อมใช้

#### 🟡 Medium Risk (Manageable challenges)
- **Shopee Orders/Products** - ต้องเป็น Managed Seller
- **TikTok Shop** - Approval delay, เริ่ม apply แต่เนิ่นๆ

#### 🔴 High Risk (May need alternative approach)
- **LINE Ads** - อาจไม่มี public API → ใช้ CSV export
- **Shopee Ads** - ไม่มี public API → ใช้ CSV export

---

## Recommendations

### Phase 1 Priority (ควรทำก่อน)

1. **Shopee/Lazada Orders & Products**
   - ข้อมูลสำคัญที่สุดสำหรับ E-commerce dashboard
   - มี API พร้อมใช้ (ตรวจสอบ Shopee Managed Seller status)

2. **Lazada Ads (LSS)**
   - มี API พร้อมใช้
   - ครอบคลุม Sponsored Discovery

3. **TikTok Shop**
   - เริ่ม apply developer access ตั้งแต่วันแรก
   - รอ 5-7 วัน + อาจต้องแก้ไข

### Alternative Approaches (สำหรับ platforms ที่ไม่มี API)

| Platform | Alternative | Implementation |
|----------|-------------|----------------|
| LINE Ads | CSV Export | Weekly manual export → GCS → BigQuery |
| Shopee Ads | CSV Export | Weekly manual export → GCS → BigQuery |

### Questions for Customer

ก่อนเริ่มพัฒนา ต้องยืนยันกับลูกค้า:

1. **Shopee**
   - [ ] ลูกค้าเป็น Shopee Managed Seller หรือไม่?
   - [ ] มี Shopee Partner account หรือยัง?

2. **LINE Ads**
   - [ ] ลูกค้าใช้ LINE Ads หรือไม่?
   - [ ] ถ้าใช้ มี LINE Official Account หรือไม่?
   - [ ] ยอมรับ manual CSV export ได้ไหม?

3. **Shopee Ads**
   - [ ] ลูกค้าใช้ Shopee Ads หรือไม่?
   - [ ] ใช้ In-Platform หรือ Off-Platform (Facebook/IG)?
   - [ ] ยอมรับ manual CSV export ได้ไหม?

4. **Priority**
   - [ ] Platforms ไหนสำคัญที่สุด?
   - [ ] ยอมรับ data delay สำหรับบาง platforms ได้ไหม?

---

## Mitigation Strategies

### Rate Limiting

```python
# Implement in BaseExtractor
RATE_LIMITS = {
    "shopee": {"requests_per_minute": 100, "retry_after": 60},
    "lazada": {"requests_per_minute": 50, "retry_after": 60},
    "tiktok_shop": {"requests_per_minute": 100, "retry_after": 60},
}

# Exponential backoff
def retry_with_backoff(func, max_retries=3, base_delay=1):
    for attempt in range(max_retries):
        try:
            return func()
        except RateLimitError:
            delay = base_delay * (2 ** attempt)
            time.sleep(delay)
    raise MaxRetriesExceeded()
```

### Token Management

```python
# Secure token storage with auto-refresh
class TokenManager:
    def __init__(self, platform: str):
        self.platform = platform
        self.secret_client = SecretManagerClient()

    def get_access_token(self) -> str:
        token = self.secret_client.get(f"{self.platform}_access_token")
        if self.is_expired(token):
            token = self.refresh_token()
            self.secret_client.set(f"{self.platform}_access_token", token)
        return token

    def refresh_token(self) -> str:
        # Platform-specific refresh logic
        pass
```

### CSV Upload Fallback

```python
# For platforms without API (LINE Ads, Shopee Ads)
class CSVUploader:
    def __init__(self, bucket_name: str):
        self.storage_client = storage.Client()
        self.bucket = self.storage_client.bucket(bucket_name)

    def upload_and_load(self, file_path: str, table_id: str):
        # Upload to GCS
        blob = self.bucket.blob(f"uploads/{file_path}")
        blob.upload_from_filename(file_path)

        # Load to BigQuery
        job_config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.CSV,
            skip_leading_rows=1,
            autodetect=True,
        )
        uri = f"gs://{self.bucket.name}/uploads/{file_path}"
        load_job = bq_client.load_table_from_uri(uri, table_id, job_config=job_config)
        load_job.result()
```

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | Dec 2025 | - | Initial risk assessment |
