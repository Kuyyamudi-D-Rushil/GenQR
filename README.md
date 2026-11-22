# Cloud-Based QR Code Generator

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.1.3-black.svg)](https://flask.palletsprojects.com/)
[![Database](https://img.shields.io/badge/Database-PostgreSQL-336791.svg)](https://www.postgresql.org/)
[![Cloud](https://img.shields.io/badge/Hosted%20On-Render-46E3B7.svg)](https://render.com/)
[![Tests](https://img.shields.io/badge/Tests-15%20Passed-brightgreen.svg)]()

> A full-stack cloud computing mini-project demonstrating stateless web application deployment, cloud database persistence, user authentication, and on-demand QR code generation using **Python Flask**, **Render**, and **Managed PostgreSQL**.

---

## 📌 Executive Summary

Traditional QR code generators either store generated images on local web server filesystems or lack user management entirely. When deployed on modern cloud container platforms (such as Render, Heroku, or AWS ECS), local filesystems are **ephemeral** and reset on every redeployment or container restart.

This project solves this challenge by implementing a **cloud-native architecture**:
1. Encoded QR content, metadata, color configurations, and user relationships are persisted in a **cloud relational database (Render PostgreSQL)**.
2. QR images are generated **statelessly and on-the-fly in server memory** using Python's `qrcode` and `Pillow` libraries, then streamed directly to the client browser as PNG streams.
3. Users can securely register, log in, generate customizable QR codes (URLs, plain text, emails, phone numbers), manage their generation portfolio, and download high-resolution PNG assets from any internet-connected device.

---

## 🏛️ System Architecture

The application implements a clean **3-Tier Cloud Architecture**:

```
+-------------------------------------------------------------------------+
|                         PRESENTATION LAYER                              |
|   Browser (Desktop / Tablet / Mobile)                                   |
|   - HTML5, CSS3, Modern Glassmorphism SaaS UI                           |
|   - Bootstrap 5.3 + Bootstrap Icons                                     |
|   - Vanilla JavaScript (Fetch API, Live Canvas, Color Sync, DOM Ops)    |
+-------------------------------------------------------------------------+
                                    │  ▲
                  HTTP / HTTPS REST │  │  JSON Metadata
                  Requests (CSRF)   │  │  PNG Stream
                                    ▼  │
+-------------------------------------------------------------------------+
|                         APPLICATION LAYER                               |
|   Render Cloud Web Service (Linux Container)                            |
|   - Gunicorn (WSGI HTTP Server)                                         |
|   - Python 3.12 + Flask 3                                               |
|   - Modular Blueprints: Auth, Generator, History                        |
|   - Flask-Login (Session & Multi-Tenant Isolation)                      |
|   - In-Memory QR Engine (qrcode + Pillow / BytesIO)                     |
+-------------------------------------------------------------------------+
                                    │  ▲
                         SQLAlchemy │  │  Structured
                         Query / DDL│  │  Records
                                    ▼  │
+-------------------------------------------------------------------------+
|                            DATA LAYER                                   |
|   Render Managed PostgreSQL Database                                    |
|   - users table (Credentials hashed with PBKDF2/Werkzeug)               |
|   - qr_codes table (Relational foreign key, cascade delete)             |
|   - Flask-Migrate (Alembic schema migrations)                           |
+-------------------------------------------------------------------------+
```

### End-to-End Request Lifecycle
1. **User Action:** The user enters a target (e.g., `https://google.com`), selects brand colors (`#4F46E5` foreground, `#FFFFFF` background), and clicks "Generate & Save".
2. **Transport:** The browser issues a `POST /api/generate` request containing JSON payload and `X-CSRFToken` header.
3. **Validation & Auth:** Flask validates data formats (valid URL pattern, 6-digit hex color regex, contrast requirements) and confirms the session identity via Flask-Login.
4. **Relational Persistence:** The QR metadata (title, type, raw content, foreground, background, timestamp) is committed to the cloud database linked to `current_user.id`.
5. **In-Memory Rendering:** Python's `qrcode` and `Pillow` libraries generate the QR pixel matrix in an in-memory `io.BytesIO` buffer without writing to disk.
6. **Delivery:** The binary PNG stream is returned with `mimetype="image/png"` and custom headers (`X-QR-ID`).
7. **Client Presentation:** JavaScript creates a local blob object URL, renders the preview, and updates the download link.
8. **Subsequent Access:** Later, when the user visits their **History** or **Dashboard**, the image is regenerated on demand via `GET /api/qr/<id>/image`.

---

## 🗄️ Database Schema Design

### Table 1: `users`
| Column Name | Data Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | `PRIMARY KEY`, Auto-increment | Unique identifier for user |
| `username` | `VARCHAR(100)` | `NOT NULL` | Display username |
| `email` | `VARCHAR(255)` | `UNIQUE`, `NOT NULL`, `INDEX` | Unique login email |
| `password_hash` | `VARCHAR(255)` | `NOT NULL` | Werkzeug salted cryptographic hash |
| `created_at` | `TIMESTAMP` | `DEFAULT UTC NOW` | Account creation timestamp |

### Table 2: `qr_codes`
| Column Name | Data Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | `PRIMARY KEY`, Auto-increment | Unique QR record ID |
| `user_id` | `INTEGER` | `FOREIGN KEY(users.id)`, `CASCADE` | Owner reference |
| `title` | `VARCHAR(150)` | Default `'My QR Code'` | Descriptive label |
| `qr_type` | `VARCHAR(30)` | `NOT NULL` (`url`, `text`, `email`, `phone`) | Information type |
| `content` | `TEXT` | `NOT NULL` | Raw encoded payload |
| `foreground` | `VARCHAR(7)` | Default `'#000000'` | 6-character hex color |
| `background` | `VARCHAR(7)` | Default `'#FFFFFF'` | 6-character hex color |
| `created_at` | `TIMESTAMP` | `DEFAULT UTC NOW`, `INDEX` | Generation timestamp |

> **Composite Index:** `ix_qr_codes_user_created` on `(user_id, created_at)` accelerates paginated user history queries.

---

## 🛠️ Technology Stack

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Frontend** | HTML5, CSS3, JavaScript (ES6+) | Modern responsive user interface |
| **Styling** | Bootstrap 5.3 + Custom CSS | Glassmorphism SaaS aesthetics, dark theme |
| **Backend Framework** | Python Flask 3 | REST API routes, template rendering, controllers |
| **WSGI Server** | Gunicorn | Production-ready HTTP server on Render |
| **QR Engine** | `qrcode[pil]` + `Pillow` | In-memory QR code generation |
| **ORM** | Flask-SQLAlchemy 3 + SQLAlchemy 2 | Object-Relational Mapping |
| **Migrations** | Flask-Migrate + Alembic | Versioned database schema evolution |
| **Authentication** | Flask-Login | User sessions and access control |
| **Password Security** | Werkzeug (`generate_password_hash`) | Cryptographic password hashing |
| **CSRF Protection** | Flask-WTF (`CSRFProtect`) | Protection against CSRF attacks |
| **Rate Limiting** | Flask-Limiter | Brute-force throttling and endpoint abuse protection |
| **Cloud Database** | Render Managed PostgreSQL | High-availability cloud persistence |
| **Hosting Platform** | Render Web Services | Cloud deployment and orchestration |
| **Test Suite** | pytest | 15 automated unit & integration tests |

---

## 📂 Project Structure

```
QRGen/
├── .env                        # Local environment variables (git-ignored)
├── .gitignore                  # Git exclusions
├── Procfile                    # Render process declaration (web: gunicorn app:app)
├── requirements.txt            # Tested Python dependency freeze
├── config.py                   # App config & Render postgres:// URL adapter
├── extensions.py               # Flask extensions (db, login_manager, csrf, migrate)
├── models.py                   # User and QRCode SQLAlchemy models
├── app.py                      # Flask application factory
│
├── routes/
│   ├── __init__.py             # Route package init
│   ├── auth.py                 # Register, login, logout routes
│   ├── generator.py            # QR generation, on-the-fly rendering, download
│   └── history.py              # Dashboard stats, history filtering, deletion
│
├── templates/
│   ├── base.html               # Global layout, navbar, CSRF meta, footer
│   ├── index.html              # Landing page, architecture showcase, public demo
│   ├── login.html              # Secure login form with show/hide password
│   ├── register.html           # Registration form with client-side checks
│   ├── dashboard.html          # Metric cards, QR generator, recent list
│   └── history.html            # Searchable, filterable QR portfolio with modal
│
├── static/
│   ├── css/
│   │   └── style.css           # Modern SaaS dark glassmorphism stylesheet
│   └── js/
│       └── main.js             # Async Fetch calls, color sync, DOM updates
│
├── migrations/                 # Alembic database migration scripts
│   ├── versions/
│   │   └── d15fa036c9da_initial_schema.py
│   └── env.py
│
└── tests/                      # Automated test suite
    ├── conftest.py             # Fixtures for app, client, auth_client
    ├── test_auth.py            # Registration, duplicate check, login, logout
    ├── test_qr.py              # QR generation, validation, dynamic rendering
    └── test_history.py         # Stats, search/filter, owner deletion, isolation
```

---

## 🚀 Local Development Setup

### 1. Clone or Open the Repository
```bash
git clone <YOUR_REPOSITORY_URL>
cd QRGen
```

### 2. Configure Virtual Environment & Install Dependencies
```bash
# Create virtual environment
python -m venv venv

# Activate on Windows:
.\venv\Scripts\activate

# Activate on macOS/Linux:
source venv/bin/activate

# Install required packages
pip install -r requirements.txt
```

### 3. Setup Local Environment Variables
A sample `.env` file is included:
```env
SECRET_KEY=your-local-development-secret-key-min-32-chars
DATABASE_URL=sqlite:///qr_generator.db
FLASK_DEBUG=1
FLASK_ENV=development
```

### 4. Initialize Database
```bash
flask --app app db upgrade
```

### 5. Run the Application
```bash
python app.py
```
Open your browser and navigate to: `http://127.0.0.1:5000`

---

## 🧪 Running the Test Suite

The test suite covers authentication, QR matrix generation, input validation, cloud database queries, and multi-tenant security isolation:

```bash
python -m pytest -v
```

Expected result:
```
tests/test_auth.py::test_register_success PASSED                         [  6%]
tests/test_auth.py::test_register_duplicate_email PASSED                 [ 13%]
tests/test_auth.py::test_register_password_mismatch PASSED               [ 20%]
tests/test_auth.py::test_register_short_password PASSED                  [ 26%]
tests/test_auth.py::test_login_success_and_logout PASSED                 [ 33%]
tests/test_auth.py::test_login_invalid_credentials PASSED                [ 40%]
tests/test_history.py::test_dashboard_stats PASSED                       [ 46%]
tests/test_history.py::test_history_filtering PASSED                     [ 53%]
tests/test_history.py::test_delete_qr_record PASSED                      [ 60%]
tests/test_history.py::test_cross_user_delete_prevention PASSED          [ 66%]
tests/test_qr.py::test_generate_qr_url PASSED                            [ 73%]
tests/test_qr.py::test_generate_qr_validation_errors PASSED              [ 80%]
tests/test_qr.py::test_retrieve_qr_image_dynamic PASSED                  [ 86%]
tests/test_qr.py::test_cross_user_isolation_prevent_access PASSED        [ 93%]
tests/test_qr.py::test_public_preview_endpoint PASSED                    [100%]
============================= 15 passed in ~2.0s ==============================
```

---

## ☁️ Step-by-Step Render Cloud Deployment

### Step 1: Push Code to GitHub
```bash
git init
git add .
git commit -m "feat: complete cloud-based QR code generator"
git branch -M main
git remote add origin https://github.com/<YOUR_USERNAME>/cloud-qr-generator.git
git push -u origin main
```

### Step 2: Create Managed PostgreSQL on Render
1. Sign in to [Render Dashboard](https://dashboard.render.com/).
2. Click **New +** → **PostgreSQL**.
3. Name: `cloud-qr-db`
4. Database Name: `cloud_qr_db`
5. User: `qr_admin`
6. Region: Choose the region nearest to you (e.g., *Singapore*, *Frankfurt*, *Oregon*).
7. Plan: **Free** (or Starter).
8. Click **Create Database**.
9. Once provisioned, locate the **Internal Database URL** (e.g., `postgres://qr_admin:...@dpg-...:5432/cloud_qr_db`) and copy it.

### Step 3: Create Web Service on Render
1. In Render Dashboard, click **New +** → **Web Service**.
2. Connect your GitHub repository `cloud-qr-generator`.
3. Configure the settings:
   - **Name:** `cloud-qr-generator`
   - **Language / Runtime:** `Python 3`
   - **Branch:** `main`
   - **Region:** Same region as your PostgreSQL instance!
   - **Build Command:** `pip install -r requirements.txt && flask --app app db upgrade`
   - **Start Command:** `gunicorn app:app`
   - **Instance Type:** `Free`

### Step 4: Configure Environment Variables
Under the **Environment** tab of your Render Web Service, add two variables:

| Key | Value | Purpose |
| :--- | :--- | :--- |
| `SECRET_KEY` | *(A long random hex string)* | Signs session cookies and CSRF tokens |
| `DATABASE_URL` | *(Paste Internal Database URL from Step 2)* | Connects Flask to Render PostgreSQL |

*(To generate a secure 64-character secret key locally, run `python -c "import secrets; print(secrets.token_hex(32))"`).*

### Step 5: Deploy and Verify
1. Click **Create Web Service**.
2. Render builds the environment, installs packages, runs database migrations, and binds Gunicorn to the production port.
3. Access your live application at:
   `https://cloud-qr-generator.onrender.com`

---

## 🔌 REST API Reference

| Method | Endpoint | Auth Required | Description | Request Body / Params |
| :--- | :--- | :---: | :--- | :--- |
| `GET` | `/` | No | Public landing page with live sandbox | None |
| `GET` | `/register` | No | Registration page | None |
| `POST` | `/register` | No | Creates new user account | `username`, `email`, `password`, `confirm_password` |
| `GET` | `/login` | No | Login page | None |
| `POST` | `/login` | No | Authenticates user session (10 req/min limit) | `email`, `password`, `remember` |
| `POST` | `/logout` | **Yes** | Terminates session (CSRF protected) | None |
| `GET` | `/dashboard` | **Yes** | User metrics, fast generator, recent list | None |
| `GET` | `/history` | **Yes** | Server-paginated QR portfolio | Query: `?type=url&q=search&sort=newest&page=1&per_page=9` |
| `POST` | `/api/generate` | **Yes** | Generates QR, persists to DB, streams PNG | `{ "title", "qr_type", "content", "foreground", "background" }` |
| `POST` | `/api/preview` | No | Public instant preview (20 req/min limit) | `{ "content", "qr_type", "foreground", "background" }` |
| `GET` | `/api/qr/<id>/image` | **Yes** | Dynamically regenerates stored QR PNG | None |
| `GET` | `/api/qr/<id>/download`| **Yes** | Downloads QR PNG with custom filename | None |
| `DELETE`| `/api/qr/<id>` | **Yes** | Deletes user's QR record from cloud DB | None |

---

## 🎓 Viva / Academic Project Defense Q&A

### 1. What makes this project a "Cloud" application rather than just a local Python script?
> **Answer:** A local Python script generates an image on a local hard drive. This application is deployed on cloud infrastructure (Render), accepts requests over HTTPS, uses stateless server instances (Gunicorn/Flask), and stores relational data in a managed cloud database (Render PostgreSQL). Even if the server container is destroyed or redeployed, user accounts and QR records remain permanently accessible from any device.

### 2. Why did you choose PostgreSQL over SQLite for production?
> **Answer:** SQLite stores data in a single local file. On cloud container platforms like Render, the container filesystem is ephemeral; files written during execution are wiped whenever the service redeploys, scales, or sleeps. PostgreSQL is an independent, managed cloud service providing persistent, scalable, relational ACID storage that survives deployments.

### 3. Why don't you save the generated PNG files to disk or AWS S3?
> **Answer:** Storing raw images creates unnecessary storage costs, maintenance overhead, and filesystem dependency. Because a QR code is entirely deterministic based on its content, error-correction level, and color values, storing a lightweight text row in PostgreSQL (~100 bytes) and dynamically rendering the image in memory takes under 5 milliseconds. This eliminates file storage costs entirely while maintaining high performance.

### 4. How does the application handle multi-tenant isolation and security?
> **Answer:** 
> - **Authentication:** User passwords are never stored in plaintext; they are hashed using Werkzeug's PBKDF2 with SHA-256 and unique salts.
> - **Authorization:** Every database retrieval and deletion query filters strictly by both `id` and `user_id = current_user.id`. User B cannot view, regenerate, or delete User A's QR code.
> - **CSRF Protection:** State-changing requests (form submits, asynchronous POST and DELETE requests) require valid CSRF tokens verified by `Flask-WTF`.
> - **Input Validation:** Content length is capped at 2,048 characters, phone numbers and URLs are regex-validated, and foreground/background hex codes are checked to prevent unreadable codes.

### 5. What happens during Render's database URL handling?
> **Answer:** Render provides PostgreSQL connection URLs starting with `postgres://`. However, SQLAlchemy 1.4+ deprecated `postgres://` in favor of `postgresql://`. The `config.py` module automatically transforms `postgres://` to `postgresql://` before initializing the database engine, ensuring seamless deployment without manual string editing.

---

## 📄 License
This project is open-source and developed for academic demonstration and learning in Cloud Computing Technology.
