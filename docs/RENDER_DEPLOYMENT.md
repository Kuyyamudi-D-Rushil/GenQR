# RENDER CLOUD DEPLOYMENT GUIDE
**Project:** Cloud-Based QR Code Generator  
**Hosting Platform:** Render (Web Service + Managed PostgreSQL)  
**Container Runtime:** Python 3.12 / Ubuntu Linux  
**Process Manager:** Gunicorn WSGI Server  

---

## 1. Overview of Cloud Components on Render

This application uses two native Render components:
1. **Render Managed PostgreSQL**:
   - Stores persistent user identities, password hashes, and QR code metadata.
   - Provides internal secure private networking within Render's data center region.
2. **Render Web Service**:
   - Executes the Flask application behind Gunicorn workers.
   - Automatically provisions TLS/SSL certificates and handles custom domain routing.
   - Runs database migrations automatically on each code deployment.

---

## 2. Option A: Automated Deployment via Render Blueprint (Recommended)

The repository includes a declarative Infrastructure-as-Code (IaC) specification file: [`render.yaml`](../render.yaml).

### Steps:
1. Push your latest code changes to your GitHub repository.
2. Log in to the [Render Cloud Dashboard](https://dashboard.render.com).
3. Click **"New +"** in the top right navigation and select **"Blueprint"**.
4. Connect your GitHub repository (`QRGen`).
5. Render will automatically detect `render.yaml` and display the resources to be created:
   - Web Service: `cloud-qr-generator`
   - Database: `cloud-qr-db`
6. Click **"Apply"**. Render will provision the PostgreSQL database, automatically link the internal database connection string, execute `flask db upgrade`, and start the Gunicorn server.

---

## 3. Option B: Manual Configuration via Render Dashboard

If you prefer to configure your services manually:

### Step 3.1: Create Render Managed PostgreSQL Database
1. Go to **Dashboard** &rarr; **"New +"** &rarr; **"PostgreSQL"**.
2. Set the database parameters:
   - **Name:** `cloud-qr-db`
   - **Database:** `cloud_qr_db`
   - **User:** `cloud_qr_user`
   - **Region:** `Oregon (US West)` (or your preferred region)
   - **Plan:** `Free`
3. Click **"Create Database"**.
4. Once provisioned, locate the **"Internal Database URL"** (e.g. `postgres://cloud_qr_user:PASSWORD@dpg-xxx-a:5432/cloud_qr_db`). Copy this URL.

### Step 3.2: Create Render Web Service
1. Go to **Dashboard** &rarr; **"New +"** &rarr; **"Web Service"**.
2. Connect your GitHub repository.
3. Configure the service settings:
   - **Name:** `cloud-qr-generator`
   - **Region:** Choose the same region as your database (e.g., `Oregon`).
   - **Branch:** `main`
   - **Runtime:** `Python 3`
   - **Build Command:** 
     ```bash
     pip install -r requirements.txt && flask db upgrade
     ```
   - **Start Command:**
     ```bash
     gunicorn app:app
     ```
   - **Plan:** `Free`

### Step 3.3: Set Environment Variables
In the Web Service settings under **"Environment Variables"**, configure:

| Key | Value | Description |
|---|---|---|
| `FLASK_ENV` | `production` | Enables production mode and disables dev fallbacks |
| `FLASK_DEBUG` | `0` | Disables interactive debuggers and verbose stacktraces |
| `SECRET_KEY` | *(Click "Generate" on Render)* | Cryptographic key for session cookie signing |
| `DATABASE_URL` | *(Paste Internal DB URL from Step 3.1)* | PostgreSQL connection string |
| `SESSION_COOKIE_SECURE` | `true` | Restricts session cookies to HTTPS connections |

### Step 3.4: Configure Health Check Path
Under **"Advanced Settings"**:
- **Health Check Path:** `/healthz`

Render will probe `/healthz` during rolling deployments to ensure the application container is responding and the database is connected before routing live web traffic to the new instance.

---

## 4. Handling PostgreSQL URL Schemes

Render's internal connection strings often begin with `postgres://`. SQLAlchemy 1.4+ and 2.0+ deprecated `postgres://` in favor of `postgresql://`.

Our application handles this automatically in `config.py`:
```python
raw_db_url = os.getenv("DATABASE_URL", "sqlite:///qr_generator.db")
if raw_db_url.startswith("postgres://"):
    raw_db_url = raw_db_url.replace("postgres://", "postgresql://", 1)
```
No manual URL editing is required.

---

## 5. Post-Deployment Verification Checklist

Once the deployment finishes:
1. Open your assigned Render URL (e.g., `https://cloud-qr-generator.onrender.com`).
2. Verify the landing page loads with the interactive generation sandbox.
3. Test `/healthz` in your browser: verify it returns HTTP 200 with `{"status": "healthy", "database": "connected"}`.
4. Click **"Create Free Account"** (`/register`) and register a new user.
5. In the dashboard, click **"Generator Studio"** (`/generate`).
6. Generate a URL QR code for `https://google.com` with custom colors.
7. Scan the generated QR code on your mobile phone to verify it opens Google.
8. Download the PNG image to your local device.
9. Open **"QR History"** (`/history`) to confirm the record was persisted to PostgreSQL.
10. Trigger a deployment restart in Render: verify that upon restart, the QR record is still accessible and can be downloaded or inspected.
