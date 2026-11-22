# CloudQR — Render Pre-Deployment Test Execution Report

**Test Run Date:** November 22, 2026  
**Test Suite:** `pytest` 9.1.1  
**Python Runtime:** 3.12.0 (Win64 / Linux container compatible)  
**Total Tests Executed:** 48  
**Tests Passed:** 48  
**Tests Failed:** 0  
**Pass Rate:** 100%  

---

## 1. Executive Summary

A comprehensive automated test suite was executed against the **CloudQR** application in an isolated testing environment. The suite tests full-stack behavior, including user identity management, password hashing, session cookies, CSRF protection, rate limiting, semantic QR input validation, in-memory PNG matrix generation, physical QR code decoding via OpenCV, PostgreSQL aggregated metrics, server-side pagination, cross-user isolation, and container health probes.

---

## 2. Test Execution Breakdown by Category

| Category | Test File | Test Count | Result | Key Coverage |
|---|---|---|---|---|
| **Authentication & Account Security** | `tests/test_auth.py` | 8 | **8 / 8 PASSED** | User registration, email uniqueness, password mismatch rejection, minimum 12-char password enforcement, integrity error rollback, login/logout (POST-only with CSRF), profile access, and password modification. |
| **History & Dashboard Analytics** | `tests/test_history.py` | 9 | **9 / 9 PASSED** | Real PostgreSQL aggregated statistics, search filtering by title/content, type filtering, server-side pagination (preserved query params), XSS-safe plain text rendering, authorized owner deletion, rollback on deletion failure, cross-user delete prevention, and zero-write GET refreshes. |
| **QR Engine & Decoding Verification** | `tests/test_qr.py` | 20 | **20 / 20 PASSED** | URL generation, semantic URL validation, email validation (`mailto:`), phone validation (`tel:`), oversized Unicode capacity error (HTTP 400), DB error rollback, dynamic in-memory PNG streaming, cross-user image isolation, stateless preview, OpenCV physical decoding for all formats, download integrity, and safety URL-in-title auto-swap. |
| **Cloud Security & Health Probing** | `tests/test_security.py` | 6 | **6 / 6 PASSED** | Production `SECRET_KEY` enforcement, session cookie flags (`HttpOnly`, `SameSite=Lax`, `Secure`), rate limiting active on `/api/preview` (HTTP 429), container health probe (`/health` & `/healthz` returning 200), liveness probe (`/health/live`), and database failure status (HTTP 503). |
| **Commercial UI/UX Architecture** | `tests/test_ui_redesign.py` | 5 | **5 / 5 PASSED** | Main navigation theme toggle button, complete separation of Dashboard (overview only) vs QR Generator (workspace), 4 interactive format selector cards (`URL`, `Text`, `Email`, `Phone`), quick action query parameters (`?type=`), and pixel-level black-and-white QR enforcement. |
| **TOTAL** | — | **48** | **48 / 48 PASSED** | **100% SUCCESS** |

---

## 3. Pixel-Level QR Decoding & Color Analysis

To ensure that generated QR codes are genuine and scannable by physical cameras:
1. **OpenCV Independent Decoding**:
   - `test_generate_and_decode_google_url`: PNG bytes from `/api/generate` decoded via `cv2.QRCodeDetector()`. Result: `https://www.google.com` (Exact match).
   - `test_generate_and_decode_different_url`: Downloaded PNG decoded via `cv2.QRCodeDetector()`. Result: `https://en.wikipedia.org/wiki/Cloud_computing` (Exact match).
   - `test_generate_and_decode_plain_text_message`: Result: `Project Verification: Cloud-Based QR Generator 2026 Genuine Output` (Exact match).
   - `test_qr_decoding_verification_email`: Result: `mailto:contact@organization.org` (Normalized scheme match).
   - `test_qr_decoding_verification_phone`: Result: `tel:+15558675309` (Normalized scheme match).
2. **Binary Black-and-White Enforcement**:
   - `test_backend_enforces_black_and_white_even_with_color_payload` and `test_black_and_white_qr_enforcement_in_generator` analyzed the complete RGB pixel color histogram using Pillow.
   - Tested sending custom color parameters (`#FF0000`, `#00FF00`).
   - Verified that all pixels in the generated image consist strictly of `(0, 0, 0)` and `(255, 255, 255)`.

---

## 4. Bugs Found & Fixed During Pre-Deployment Audit

1. **Missing `/health` Route Alias**:
   - *Finding*: Render's default health check may probe `/health` or `/healthz`. The app originally had only `/healthz`.
   - *Fix*: Added `@app.route('/health')` alongside `@app.route('/healthz')` and implemented a dedicated `/health/live` probe.
2. **PostgreSQL Idle Connection Stale Drop**:
   - *Finding*: Render managed PostgreSQL closes idle connections after periods of inactivity, causing unhandled `OperationalError` exceptions on subsequent requests.
   - *Fix*: Added `SQLALCHEMY_ENGINE_OPTIONS` with `pool_pre_ping=True` and `pool_recycle=300` in `config.py`.
3. **Missing Port Dynamic Binding**:
   - *Finding*: Gunicorn defaults to port 8000 when `--bind` is omitted, whereas Render assigns dynamic ports via `$PORT` (default 10000).
   - *Fix*: Added `gunicorn.conf.py` dynamically reading `PORT` from environment variables.
4. **Missing Environment Template**:
   - *Finding*: Developers and DevOps engineers lacked an `.env.example` file.
   - *Fix*: Created clean `.env.example` with clear placeholders and zero secrets.

---

## 5. Tests Not Executed / Remaining Risks

- **Tests Not Executed**: Live production database stress testing (e.g. 10,000 concurrent writes) was not run locally because production infrastructure has not yet been provisioned.
- **Remaining External Risks**:
  1. *Free-Tier Inactivity Sleep*: Render free-tier web services spin down after 15 minutes of inactivity. The initial incoming request will take ~30–50 seconds to wake the service.
  2. *Render Free-Tier PostgreSQL Expiry*: Render's free PostgreSQL tier expires after 30 days. For long-term production, upgrading to a Starter tier or backing up data is required.
