# CloudQR — Render Production Deployment Checklist & Step-by-Step Guide

**Document Version:** 1.0.0  
**Target:** Render Cloud Platform  
**Target Architecture:** Flask 3 + Gunicorn + Render PostgreSQL (Oregon Region)  

---

## 1. Pre-Deployment Verification Checklist

Before deploying, ensure the following requirements are met:

- [x] All 48 automated tests pass (`python -m pytest -v`).
- [x] Git working directory is clean and pushed to GitHub (`main` branch).
- [x] `.env` is listed in `.gitignore` and has NEVER been committed to Git.
- [x] `.env.example` is present with placeholder values only.
- [x] `requirements.txt` contains all necessary dependencies.
- [x] `Procfile` and `gunicorn.conf.py` are present in repository root.
- [x] Database migrations are up-to-date (`flask db heads` shows `e10f718140c4`).
- [x] Health check endpoints `/health` and `/healthz` are functional.

---

## 2. Deployment Method A: Infrastructure as Code via `render.yaml` (Recommended)

Because the project includes a configured `render.yaml` blueprint, Render can automatically provision both the **Web Service** and the **PostgreSQL Database** in a single click:

1. Log into your [Render Dashboard](https://dashboard.render.com).
2. Click **Blueprints** in the top navigation.
3. Click **New Blueprint Instance**.
4. Connect your GitHub account and select the **GenQR** repository:
   ```
   https://github.com/Kuyyamudi-D-Rushil/GenQR.git
   ```
5. Choose branch: `main`.
6. Render will automatically read `render.yaml`, set up:
   - Web Service: `cloud-qr-generator` (Python runtime, Oregon region)
   - Database: `cloud-qr-db` (PostgreSQL, Oregon region)
   - Environment variables: `SECRET_KEY` (auto-generated), `DATABASE_URL` (mapped from database), `SESSION_COOKIE_SECURE=true`.
7. Click **Apply**.
8. Wait for the build and deployment to complete (~2–3 minutes).

---

## 3. Deployment Method B: Manual Dashboard Setup

If you prefer to configure the services manually through the Render UI:

### Step 1: Create the Managed PostgreSQL Database
1. In the Render Dashboard, click **New +** > **PostgreSQL**.
2. Configure settings:
   - **Name**: `cloud-qr-db`
   - **Database**: `cloud_qr_db`
   - **User**: `cloud_qr_user`
   - **Region**: `Oregon (US West)` *(Note this region; your web service must be in the same region!)*
   - **Plan**: `Free`
3. Click **Create Database**.
4. Wait for status to show **Available**.
5. Scroll down to **Connections** and copy the **Internal Database URL** (e.g., `postgres://cloud_qr_user:...@dpg-...-a/cloud_qr_db`).

---

### Step 2: Create the Python Web Service
1. In the Render Dashboard, click **New +** > **Web Service**.
2. Select **Build and deploy from a Git repository**.
3. Select your repository: `Kuyyamudi-D-Rushil/GenQR`.
4. Configure basic settings:
   - **Name**: `cloud-qr-generator`
   - **Region**: `Oregon (US West)` *(Must match the database region!)*
   - **Branch**: `main`
   - **Root Directory**: *(Leave blank)*
   - **Runtime**: `Python 3`
   - **Build Command**:
     ```bash
     pip install -r requirements.txt && flask db upgrade
     ```
   - **Start Command**:
     ```bash
     gunicorn app:app
     ```
   - **Plan Type**: `Free`

---

### Step 3: Configure Environment Variables
In the **Environment** section of your new Web Service, add the following variables:

| Key | Value | Notes |
|---|---|---|
| `FLASK_ENV` | `production` | Enables production mode |
| `FLASK_DEBUG` | `0` | Disables debug mode and traces |
| `SECRET_KEY` | *(Generate a 64-char token)* | Run `python -c "import secrets; print(secrets.token_hex(32))"` |
| `DATABASE_URL` | *(Paste Internal Database URL from Step 1)* | Automatically converted to `postgresql://` |
| `SESSION_COOKIE_SECURE` | `true` | Restricts cookies to HTTPS |
| `PYTHON_VERSION` | `3.12.0` | Matches tested runtime |

---

### Step 4: Configure Health Check
1. Scroll down to **Advanced Settings**.
2. Set **Health Check Path** to:
   ```
   /healthz
   ```
3. Click **Create Web Service**.

---

## 4. Post-Deployment Smoke Verification

Once Render displays **Deploy live**:

1. **Verify Health Endpoint**:
   ```bash
   curl -i https://<your-subdomain>.onrender.com/healthz
   ```
   Expected response:
   ```json
   {
     "status": "healthy",
     "database": "connected",
     "service": "cloud-qr-generator",
     "timestamp": "..."
   }
   ```

2. **Verify User Registration & Login**:
   - Open `https://<your-subdomain>.onrender.com/register` in your browser.
   - Register a new account (username, email, password >= 12 chars).
   - Ensure you are redirected to the Dashboard.

3. **Verify QR Code Generation**:
   - On the Dashboard, click **+ Create QR Code**.
   - Generate a URL QR code for `https://www.google.com`.
   - Verify that the QR image displays on the preview canvas.
   - Click **Download PNG** and scan the downloaded code with your phone camera.

4. **Verify Cloud Database Persistence**:
   - Go to **QR History**. Ensure your generated code is listed.
   - Log out, clear cookies, and log back in.
   - Verify that all records remain intact in PostgreSQL.

5. **Verify Dark/Light Theme Switcher**:
   - Click the theme toggle icon in the navigation bar.
   - Verify that all cards, tables, inputs, and text transition smoothly.
   - Refresh the page and confirm that your preference is preserved.

---

## 5. Free-Tier Operational Notes & Best Practices

- **Inactivity Spin-Down**: On Render's free tier, the web service spins down after 15 minutes of inactivity. When a new request arrives, Render automatically spins up the container (~30–50 seconds cold-start delay).
- **PostgreSQL 30-Day Window**: Free PostgreSQL databases on Render expire 30 days after creation. For a production deployment intended to last longer, export database dumps periodically or upgrade to a Starter tier database.
- **In-Memory Rendering**: Because the app generates QR images directly in memory with Python Pillow and stores records in PostgreSQL, the service has zero dependency on ephemeral container disk storage.
