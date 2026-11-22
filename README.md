# Cloud-Based QR Code Generator

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.1.3-black.svg)](https://flask.palletsprojects.com/)
[![Database](https://img.shields.io/badge/Database-PostgreSQL-336791.svg)](https://www.postgresql.org/)
[![Cloud](https://img.shields.io/badge/Hosted%20On-Render-46E3B7.svg)](https://render.com/)
[![Tests](https://img.shields.io/badge/Tests-41%20Passed-brightgreen.svg)]()

> A production-grade cloud computing application demonstrating stateless web application deployment, managed cloud relational database persistence, secure multi-tenant authentication, and dynamic on-demand QR code generation using **Python Flask**, **Render**, and **Managed PostgreSQL**.

---

## Table of Contents
1. [Project Overview](#1-project-overview)
2. [Problem Statement](#2-problem-statement)
3. [Objectives](#3-objectives)
4. [Features](#4-features)
5. [Technology Stack](#5-technology-stack)
6. [System Architecture](#6-system-architecture)
7. [Cloud Computing Concepts](#7-cloud-computing-concepts)
8. [Database Design](#8-database-design)
9. [Folder Structure](#9-folder-structure)
10. [Local Setup](#10-local-setup)
11. [Environment Variables](#11-environment-variables)
12. [Running Instructions](#12-running-instructions)
13. [Testing Instructions](#13-testing-instructions)
14. [Render Deployment Instructions](#14-render-deployment-instructions)
15. [Screenshots & UI Walkthrough](#15-screenshots--ui-walkthrough)

---

## 1. Project Overview
The **Cloud-Based QR Code Generator** is a complete, cloud-hosted web application that enables users to generate high-resolution, scannable QR codes for diverse information formats (web URLs, plain text, email `mailto:` links, and phone `tel:` links), customize foreground and background colors, download high-definition PNG images, and store their generated QR assets securely in a cloud database. Registered users can access their generation history, view real-time aggregated dashboard analytics, and manage their portfolio from any internet-connected device.

---

## 2. Problem Statement
Traditional QR code generator utilities suffer from two critical architectural shortcomings:
1. **Local Ephemeral Storage Loss:** In modern cloud Platform-as-a-Service (PaaS) and container environments (such as Render, Heroku, AWS ECS), the local container filesystem is ephemeral. Any files written to local disk are wiped whenever an instance restarts, scales, or redeploys. Saving images to local disk leads to complete asset loss.
2. **Lack of Centralized Multi-User Management:** Standard tools do not provide authenticated multi-user portfolios, search capabilities, or persistent asset regeneration, requiring users to manually archive images on their personal devices.

---

## 3. Objectives
- **Demonstrate Cloud-Native Architecture:** Build a decoupled 3-tier cloud application using Python Flask and PostgreSQL on the Render cloud platform.
- **Solve the Ephemeral Disk Dilemma:** Persist lightweight QR parameters and metadata in a managed cloud database, regenerating images statelessly on-the-fly in server memory (`io.BytesIO`) without relying on ephemeral disks or external blob storage.
- **Ensure Multi-Tenant Isolation:** Implement cryptographic authentication (Werkzeug password hashing), secure session management (Flask-Login, HTTP-only Lax cookies), and row-level user scoping.
- **Provide Genuine Functionality:** Generate genuine, scannable QR codes using Python's `qrcode` and `Pillow` libraries, validated via computer-vision automated decoding tests.

---

## 4. Features
- **Multi-Format QR Generation:**
  - **URLs:** Normalizes domains and automatically validates HTTP/HTTPS protocols.
  - **Plain Text:** Encodes arbitrary text payloads up to 2,048 bytes.
  - **Email:** Semantic RFC 5322 email syntax validation, normalized to `mailto:`.
  - **Phone Numbers:** E.164 phone digit length validation, normalized to `tel:`.
- **Visual Customization & Live Previews:**
  - Real-time color pickers with hex synchronization.
  - Contrast validation preventing unreadable combinations.
  - Quick curated palette presets (Classic Monochrome, Indigo Tech, Emerald, Ruby, Royal Violet).
  - High-resolution PNG output at Error Correction Level M (15% error recovery).
- **Persistent Cloud Portfolio & History:**
  - Server-side pagination with secondary deterministic ID sort.
  - Multi-term search queries across title and encoded content.
  - Category type filtering (URL, text, email, phone).
  - Detailed modal inspection with XSS-safe DOM attribute binding.
  - Accessible deletion with automatic count and empty-state updates.
- **Dedicated Application Pages:**
  - **Landing Page (`/`):** Showcase of capabilities, 3-tier architecture, and public stateless generation sandbox.
  - **User Dashboard (`/dashboard`):** Real-time database metrics (Total Saved, Generated Today, Type Breakdown) and recent generations list.
  - **Generator Studio (`/generate`):** Dedicated standalone workspace for generation and live testing.
  - **History Archive (`/history`):** Complete portfolio management with server-side pagination.
  - **User Profile (`/profile`):** Account identity details, cloud storage tier info, and secure password modification.
  - **Health Check (`/healthz`):** Active container orchestration probe verifying database connectivity.

---

## 5. Technology Stack

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Frontend** | HTML5, CSS3, JavaScript (ES6+) | Semantic markup, responsive glassmorphism UI |
| **UI Framework** | Bootstrap 5.3.3 + Bootstrap Icons | Responsive grid system, modal dialogs, accessible elements |
| **Backend Framework** | Python 3.12 + Flask 3.1.3 | REST API controllers, template rendering, blueprints |
| **WSGI Server** | Gunicorn 21.2+ | Production-grade pre-fork worker HTTP server |
| **QR Engine** | `qrcode[pil] 8.2+` + `Pillow 13.0+` | In-memory 2D matrix generation and PNG rendering |
| **Database ORM** | Flask-SQLAlchemy 3.1+ | Relational schema modeling and connection pooling |
| **Database Migrations** | Flask-Migrate 4.1+ (Alembic) | Version-controlled database schema evolution |
| **Authentication** | Flask-Login 0.6+ | Session persistence and user loader management |
| **Password Security** | Werkzeug | PBKDF2/SHA-256 salted password hashing |
| **CSRF Protection** | Flask-WTF 1.3+ | CSRF token validation on state-changing requests |
| **Rate Limiting** | Flask-Limiter 4.1+ | Throttling login brute-force and preview abuse |
| **Cloud Database** | Render Managed PostgreSQL | High-availability relational cloud persistence |
| **Cloud Hosting** | Render Web Services | Linux container orchestration with zero-downtime health probes |
| **Verification / CV** | Pytest 9.1+ + OpenCV (`cv2`) | Automated integration testing and QR matrix decoding |

---

## 6. System Architecture

The application implements a decoupled **Three-Tier Cloud Architecture**:

```
+-----------------------------------------------------------------------------------+
|                            LAYER 1: PRESENTATION LAYER                            |
|                                                                                   |
|  - HTML5 & CSS3 with Glassmorphism Design System (Bootstrap 5.3.3)                |
|  - Responsive Client Application (Desktop, Tablet, Mobile)                        |
|  - Asynchronous HTTP/REST Requests (Fetch API, Blob Stream Handlers)             |
|  - Client-Side Color Hex Synchronizer & Live Preview Sandbox                      |
|  - Accessible History Grid & Real-time Live Announcements (ARIA live)             |
+------------------------------------------+----------------------------------------+
                                           | HTTPS / JSON / Binary Blobs
                                           v
+-----------------------------------------------------------------------------------+
|                        LAYER 2: STATELESS APPLICATION LAYER                       |
|                                                                                   |
|  - Platform: Render Web Service (Ubuntu Linux Container / Python 3.12)           |
|  - WSGI Server: Gunicorn (Pre-fork worker model)                                 |
|  - Web Framework: Python Flask (Application Factory & Blueprints)                |
|  - Authentication: Flask-Login with Secure Lax/HttpOnly Cookie Management        |
|  - Security & Throttling: Flask-Limiter, Flask-WTF CSRF Protection               |
|  - Input Validation: Semantic URL, RFC 5322 Email, E.164 Phone Normalization     |
|  - Image Generation: Python qrcode + Pillow (In-Memory BytesIO Buffering)         |
|  - Health & Diagnostics: /healthz Active Database Ping Probe                     |
+------------------------------------------+----------------------------------------+
                                           | Connection Pool / SSL TCP Socket
                                           v
+-----------------------------------------------------------------------------------+
|                          LAYER 3: CLOUD DATA LAYER                                |
|                                                                                   |
|  - Platform: Render Managed Cloud PostgreSQL                                      |
|  - Persistence: Dedicated Cloud Block Storage with Automatic Failover             |
|  - ORM & Abstraction: Flask-SQLAlchemy 3.1+ (Engine Connection Pooling)           |
|  - Migration Tracking: Flask-Migrate & Alembic                                    |
|  - Schema Optimization: Composite Index on (user_id, created_at)                  |
|  - Referential Integrity: Foreign Keys with ON DELETE CASCADE                     |
+-----------------------------------------------------------------------------------+
```

---

## 7. Cloud Computing Concepts

This application serves as a practical implementation of fundamental cloud computing principles:

1. **Cloud-Hosted Web Application:** Containerized application deployment on Render managed infrastructure with automated TLS and port binding.
2. **Cloud-Hosted Relational Database:** Managed PostgreSQL storage completely separated from ephemeral web nodes, providing automated backups and WAL logging.
3. **Stateless Compute & Ephemeral Disk Mitigation:** Eliminates filesystem reliance by storing generation metadata in the database and streaming rendered images directly from memory buffers (`io.BytesIO`).
4. **Client-Server Communication:** Modern RESTful contracts using standardized HTTP verbs (`GET`, `POST`, `DELETE`), JSON payloads, and binary octet streams.
5. **Multi-Tenant User Isolation:** Strict row-level database filtering enforcing that users can only access and modify their own assets (`filter_by(id=qr_id, user_id=current_user.id)`).
6. **Authentication & Session Security:** Salted PBKDF2 password hashing with cryptographically signed, `HttpOnly`, `SameSite="Lax"` session cookies.
7. **Infrastructure-as-Code (IaC):** Complete cloud resource provisioning codified in `render.yaml`.
8. **Scalability & Resiliency:** Database indexes (`ix_qr_codes_user_created`), server-side pagination, and rate limiting protect against resource exhaustion.

---

## 8. Database Design

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

> **Composite Index:** `ix_qr_codes_user_created` on `(user_id, created_at)` optimizes paginated history queries from $O(N)$ table scans to $O(\log N)$ b-tree lookups.

---

## 9. Folder Structure

```
QRGen/
├── .env                        # Local environment variables (git-ignored)
├── .gitignore                  # Git exclusions
├── Procfile                    # Render process declaration (web: gunicorn app:app)
├── render.yaml                 # Render Infrastructure-as-Code blueprint
├── requirements.txt            # Tested Python dependency freeze
├── config.py                   # App config & Render postgres:// URL adapter
├── extensions.py               # Flask extensions (db, login_manager, csrf, limiter)
├── models.py                   # User and QRCode SQLAlchemy models
├── app.py                      # Flask application factory & health-check
│
├── routes/
│   ├── __init__.py             # Route package init
│   ├── auth.py                 # Register, login, logout, profile routes
│   ├── generator.py            # Dedicated studio, QR generation, download
│   └── history.py              # Dashboard stats, paginated history, deletion
│
├── templates/
│   ├── base.html               # Global layout, navbar, CSRF meta, footer
│   ├── index.html              # Landing page, architecture showcase, sandbox
│   ├── login.html              # Secure login form with password toggle
│   ├── register.html           # Registration form with 12-char validation
│   ├── dashboard.html          # Metric cards, quick generator, recent list
│   ├── generator.html          # Dedicated QR generation studio workspace
│   ├── history.html            # Searchable, filterable QR portfolio with modal
│   └── profile.html            # User account settings and password update
│
├── static/
│   ├── css/
│   │   └── style.css           # Modern SaaS dark glassmorphism stylesheet
│   └── js/
│       └── main.js             # Async Fetch calls, color sync, DOM updates
│
├── migrations/                 # Alembic database migration scripts
│   ├── versions/
│   │   ├── d15fa036c9da_initial_schema.py
│   │   └── e10f718140c4_add_composite_index.py
│   └── env.py
│
├── docs/                       # Comprehensive Engineering Documentation
│   ├── PROJECT_AUDIT.md        # Complete component audit and classification
│   ├── IMPLEMENTATION_PLAN.md  # Technical architectural blueprint
│   ├── TEST_REPORT.md          # 37-test automated verification matrix
│   └── RENDER_DEPLOYMENT.md    # Production deployment and configuration guide
│
└── tests/                      # Automated test suite
    ├── conftest.py             # Fixtures for app, client, auth_client
    ├── test_auth.py            # Registration, duplicate check, login, profile
    ├── test_qr.py              # QR generation, validation, OpenCV decoding
    ├── test_history.py         # Stats, today query, pagination, isolation
    └── test_security.py        # Secret key check, cookies, rate limits, healthz
```

---

## 10. Local Setup

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

---

## 11. Environment Variables

Create a `.env` file in the project root:

```env
SECRET_KEY=your-local-development-secret-key-min-32-chars
DATABASE_URL=sqlite:///qr_generator.db
FLASK_DEBUG=1
FLASK_ENV=development
```

> In production on Render, `FLASK_ENV=production`, `FLASK_DEBUG=0`, `DATABASE_URL` is automatically supplied by the managed PostgreSQL service, and `SECRET_KEY` is generated automatically.

---

## 12. Running Instructions

### Initialize Database
```bash
flask db upgrade
```

### Start Development Server
```bash
python app.py
```
Open your browser and navigate to: `http://127.0.0.1:5000`

### Start with Production Gunicorn (Linux / macOS)
```bash
gunicorn app:app
```

---

## 13. Testing Instructions

The test suite contains 41 automated tests verifying authentication, semantic input validation, database rollbacks, computer-vision QR decoding, and health check probes:

```powershell
# On Windows PowerShell:
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"; python -m pytest -v

# On macOS/Linux:
python -m pytest -v
```

### Test Suite Execution Output:
```text
tests/test_auth.py::test_register_success PASSED                         [  2%]
tests/test_auth.py::test_register_duplicate_email PASSED                 [  4%]
tests/test_auth.py::test_register_password_mismatch PASSED               [  7%]
tests/test_auth.py::test_register_short_password PASSED                  [  9%]
tests/test_auth.py::test_register_integrity_error_rollback PASSED        [ 12%]
tests/test_auth.py::test_login_success_and_logout_post_only PASSED       [ 14%]
tests/test_auth.py::test_login_invalid_credentials PASSED                [ 17%]
tests/test_auth.py::test_profile_page_access_and_password_update PASSED  [ 19%]
tests/test_history.py::test_dashboard_stats PASSED                       [ 21%]
tests/test_history.py::test_history_filtering PASSED                     [ 24%]
tests/test_history.py::test_history_pagination PASSED                    [ 26%]
tests/test_history.py::test_history_xss_safe_rendering PASSED            [ 29%]
tests/test_history.py::test_delete_qr_record PASSED                      [ 31%]
tests/test_history.py::test_delete_qr_db_error_rollback PASSED           [ 34%]
tests/test_history.py::test_cross_user_delete_prevention PASSED          [ 36%]
tests/test_history.py::test_dashboard_get_creates_no_qr_records PASSED   [ 39%]
tests/test_history.py::test_dashboard_today_metric PASSED                [ 41%]
tests/test_qr.py::test_generate_qr_url PASSED                            [ 43%]
tests/test_qr.py::test_semantic_url_validation PASSED                    [ 46%]
tests/test_qr.py::test_semantic_email_validation PASSED                  [ 48%]
tests/test_qr.py::test_semantic_phone_validation PASSED                  [ 51%]
tests/test_qr.py::test_oversized_unicode_capacity_overflow PASSED        [ 53%]
tests/test_qr.py::test_generate_db_error_rollback PASSED                 [ 56%]
tests/test_qr.py::test_generate_qr_validation_errors PASSED              [ 58%]
tests/test_qr.py::test_retrieve_qr_image_dynamic PASSED                  [ 60%]
tests/test_qr.py::test_cross_user_isolation_prevent_access PASSED        [ 63%]
tests/test_qr.py::test_public_preview_endpoint PASSED                    [ 65%]
tests/test_qr.py::test_qr_decoding_verification_url PASSED               [ 68%]
tests/test_qr.py::test_qr_decoding_verification_text PASSED              [ 70%]
tests/test_qr.py::test_qr_decoding_verification_email PASSED             [ 73%]
tests/test_qr.py::test_qr_decoding_verification_phone PASSED             [ 75%]
tests/test_qr.py::test_generator_page_access PASSED                      [ 78%]
tests/test_qr.py::test_generate_and_decode_google_url PASSED             [ 80%]
tests/test_qr.py::test_generate_and_decode_different_url PASSED          [ 82%]
tests/test_qr.py::test_generate_and_decode_plain_text_message PASSED     [ 85%]
tests/test_qr.py::test_generate_safety_swap_url_in_title PASSED          [ 87%]
tests/test_security.py::test_production_secret_key_enforcement PASSED    [ 90%]
tests/test_security.py::test_session_cookie_security_flags PASSED        [ 92%]
tests/test_security.py::test_rate_limiting_active PASSED                 [ 95%]
tests/test_security.py::test_rate_limit_preview_behavior PASSED          [ 97%]
tests/test_security.py::test_health_check_endpoint PASSED                [100%]

============================= 41 passed in 5.69s ==============================
```

---

## 14. Render Deployment Instructions

Detailed step-by-step deployment instructions are documented in [`docs/RENDER_DEPLOYMENT.md`](docs/RENDER_DEPLOYMENT.md).

### Quick Blueprint Deployment:
1. Push your repository to GitHub.
2. In the [Render Dashboard](https://dashboard.render.com), click **New +** &rarr; **Blueprint**.
3. Select your repository. Render will automatically detect [`render.yaml`](render.yaml) and configure:
   - Web Service: `cloud-qr-generator`
   - Database: `cloud-qr-db` (Managed PostgreSQL)
   - Build Command: `pip install -r requirements.txt && flask db upgrade`
   - Start Command: `gunicorn app:app`
   - Health Check Path: `/healthz`
4. Click **Apply**.

---

## 15. Screenshots & UI Walkthrough

### 1. Landing Page & Architecture Showcase (`/`)
Modern glassmorphism dark SaaS design with hero section, trust badges, live generation sandbox, three-tier cloud architecture diagram, and feature breakdown.

```
+--------------------------------------------------------------------------------+
| CloudQR SaaS                     [Features] [Architecture]  [Log In] [Get Started] |
+--------------------------------------------------------------------------------+
| Next-Gen QR Code Engine with Persistent Cloud Storage                           |
|                                                                                |
| [ Create Free Account ]  [ Try Interactive Demo ]                              |
|                                                                                |
| (v) Zero Data Loss   (*) Dynamic Memory Generation   (Cloud) Render + PostgreSQL|
+--------------------------------------------------------------------------------+
```

### 2. User Dashboard (`/dashboard`)
Displays real-time database queries:
- **Total Saved QRs**
- **Generated Today** (since midnight UTC)
- **URL Codes**
- **Other Formats** (Email, Phone, Text)
- Embedded Quick Generator and Recent Cloud QR table with instant actions.

### 3. Dedicated Generator Studio (`/generate`)
A focused workspace featuring payload tabs (URL, Text, Email, Phone), title input, real-time color pickers with hex sync, preset color dots, live render preview, and instant download.

### 4. Paginated QR History (`/history`)
Portfolio of generated codes with server-side pagination, search input, type filter dropdown, sorting options, safe modal preview trigger, and deletion with atomic database rollback.

### 5. User Profile & Account Settings (`/profile`)
Tenant information card displaying Username, Email, Registration Date, Account ID, and Cloud Database tier, alongside a secure password modification form.

---

## 📄 License
This project is open-source and developed for academic demonstration and learning in Cloud Computing Technology.
