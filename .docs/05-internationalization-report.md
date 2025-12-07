# Internationalization (i18n) Readiness Analysis

**Project**: Central Marketing Dashboard
**Date**: 2025-12-07
**Status**: 🟢 **High Readiness** (Ready with Minor Adjustments)

## Executive Summary
The "Central Marketing Dashboard" is technically well-positioned for international markets, specifically within Southeast Asia (SEA). The architecture supports multi-region operations out-of-the-box with minimal code changes required.

## Key Strengths

### 1. Multi-Region Architecture
The core extractors for **Shopee** and **Lazada** are already built to support multiple countries.
*   **Lazada Extractor**: Explicitly supports `TH`, `SG`, `MY`, `VN`, `PH`, `ID` via the `REGIONAL_ENDPOINTS` configuration.
*   **Shopee Extractor**: Uses the global `partner.shopeemobile.com` endpoint which is region-agnostic, relying on shop credentials to determine the locale.

### 2. Configuration-Driven Design
The project avoids hardcoding regional values in the source code.
*   **`config/platforms.yaml`**: centralized management of API endpoints.
*   **Currency & Timezone**: Configurable via `currency.default` and `timezone.default` settings.
*   **Abstracted Logic**: Utility functions in `src/utils/currency.py` handle formatting and conversion based on these configs.

### 3. Market Fit
The tech stack (Shopee, Lazada, TikTok, Facebook, Google) covers the dominant e-commerce and advertising platforms across the entire SEA region, making the product immediately relevant in Vietnam, Indonesia, Philippines, Malaysia, and Singapore.

## Gap Analysis & Recommendations

| Area | Status | Recommendation |
| :--- | :--- | :--- |
| **Currency Conversion** | 🟡 Partial | Current implementation uses **static exchange rates** in `src/utils/currency.py`. For a commercial product, integrate a real-time exchange rate API (e.g., Fixer.io, OpenExchangeRates) to handle daily fluctuations accurately. |
| **Data Transformation** | ⚪️ Unverified | The SQL transformation layer (`sql/transformations`) appeared empty during inspection. Ensure that any future SQL logic avoids hardcoded values like `WHEN country = 'TH'`. |
| **Data Privacy** | 🔴 Action Required | Selling internationally requires compliance with local laws (e.g., PDPA in Thailand/Singapore, GDPR-like laws in Vietnam/Indonesia). Ensure data storage (BigQuery locations) complies with data residency requirements if applicable. |
| **Documentation** | 🟡 Partial | `README.md` and comments are in English (Good), but end-user documentation (dashboards) might need localization capabilities. |

## Conclusion
The project is **highly suitable for international export**. The codebase is clean, modular, and designed with regional flexibility in mind. The primary work required to "go global" is operational (legal/sales) rather than technical refactoring.
