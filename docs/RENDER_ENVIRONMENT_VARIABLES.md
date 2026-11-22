# CloudQR — Render Environment Variables Guide

**Document Version:** 1.0.0  
**Target Environment:** Render Cloud Platform (Web Service & Managed PostgreSQL)  
**Security Classification:** Public Reference / DevOps Standard  

> [!IMPORTANT]
> Never commit actual production secrets, passwords, or keys to source control. Configure all production values directly in the **Render Dashboard > Environment** tab or via Render Blueprints (`render.yaml`).

---

## 1. Summary of Environment Variables

| Variable Name | Required in Production | Default / Fallback Value | Purpose |
|---|---|---|---|
| `SECRET_KEY` | **YES (CRITICAL)** | None (Crashes safely if missing) | Cryptographic signing key for session cookies, CSRF tokens, and security hashes. |
| `DATABASE_URL` | **YES (CRITICAL)** | `sqlite:///qr_generator.db` (Dev fallback) | PostgreSQL connection string pointing to Render Managed Database. |
| `FLASK_ENV` | Recommended | `production` | Sets application execution environment. |
| `FLASK_DEBUG` | Recommended | `0` (False) | Toggles development debug tools and interactive debugger. |
| `SESSION_COOKIE_SECURE` | Recommended | `true` (When in production) | Restricts session cookies to HTTPS encrypted connections. |
| `PORT` | Auto-Injected | `10000` | Port on which the Gunicorn WSGI server listens. Injected by Render. |
| `WEB_CONCURRENCY` | Optional | `2` | Number of Gunicorn worker processes. |
| `PYTHON_GET_THREADS` | Optional | `4` | Number of worker threads per Gunicorn process. |
| `DB_POOL_SIZE` | Optional | `5` | SQLAlchemy PostgreSQL connection pool size. |
| `DB_POOL_RECYCLE` | Optional | `300` | Seconds after which database connections are recycled to prevent idle timeouts. |

---

## 2. Detailed Configuration Guide

### `SECRET_KEY`
- **Required**: **Yes**
- **Description**: Flask uses this key to cryptographically sign session cookies and generate CSRF protection tokens. If this key is compromised, sessions can be forged.
- **Security Standard**: Must be a cryptographically random, high-entropy string of at least 32 bytes (64 hexadecimal characters).
- **How to Generate**:
  Run this command in any terminal to generate a secure key:
  ```bash
  python -c "import secrets; print(secrets.token_hex(32))"
  ```
- **How to Configure on Render**:
  1. Open **Render Dashboard** > Select your Web Service.
  2. Navigate to **Environment** > Click **Add Environment Variable**.
  3. Key: `SECRET_KEY`
  4. Value: Paste your generated 64-character token.
  *(Alternatively, in `render.yaml`, `generateValue: true` automatically creates a unique secret on deploy).*

---

### `DATABASE_URL`
- **Required**: **Yes**
- **Description**: The full URI used by SQLAlchemy to connect to the cloud PostgreSQL database.
- **Format**:
  ```
  postgresql://[user]:[password]@[hostname]:5432/[database_name]
  ```
- **Scheme Auto-Normalization**:
  Render provides connection strings beginning with `postgres://`. SQLAlchemy 1.4+ and 2.0+ require `postgresql://`. The application's `config.py` automatically converts `postgres://` to `postgresql://` at startup.
- **How to Configure on Render**:
  - **Option A (Internal Connection — Recommended)**:
    1. In the Render Dashboard, open your PostgreSQL database page.
    2. Under **Connections**, copy the **Internal Database URL**.
    3. In your Web Service **Environment** tab, set `DATABASE_URL` to this value.
    *(Internal connections stay within Render's private network, saving latency and bandwidth).*
  - **Option B (render.yaml Blueprint)**:
    In `render.yaml`, the `fromDatabase` directive automatically maps the connection string:
    ```yaml
    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: cloud-qr-db
          property: connectionString
    ```

---

### `FLASK_ENV`
- **Required**: Recommended
- **Value**: `production`
- **Description**: Informs Flask and the application factory that the service is running in live production mode, activating strict cookie security, CSRF guards, and disabling development fallback keys.

---

### `FLASK_DEBUG`
- **Required**: Recommended
- **Value**: `0`
- **Description**: Must be set to `0` or `false` in production. Disables the interactive Werkzeug traceback debugger, preventing potential remote code execution and stack trace disclosure.

---

### `SESSION_COOKIE_SECURE`
- **Required**: Recommended
- **Value**: `true`
- **Description**: Ensures session cookies are transmitted exclusively over encrypted HTTPS connections provided by Render's free SSL certificate.

---

### `PORT`
- **Required**: Handled Automatically
- **Value**: `10000`
- **Description**: Render injects this variable into container environments. `gunicorn.conf.py` binds to `0.0.0.0:$PORT` dynamically so no manual override is required.

---

### `WEB_CONCURRENCY` & `PYTHON_GET_THREADS`
- **Required**: Optional (Tuning)
- **Defaults**: `WEB_CONCURRENCY=2`, `PYTHON_GET_THREADS=4`
- **Description**: Allocates 2 worker processes with 4 threads each, providing concurrency for up to 8 simultaneous requests on Render's 512MB RAM free tier without memory exhaustion.

---

## 3. Render Dashboard Environment Template

To configure your service manually, enter these values in **Environment**:

```env
FLASK_ENV = production
FLASK_DEBUG = 0
SECRET_KEY = [Paste 64-character token from secrets.token_hex(32)]
DATABASE_URL = [Paste Render PostgreSQL Internal Database URL]
SESSION_COOKIE_SECURE = true
```
