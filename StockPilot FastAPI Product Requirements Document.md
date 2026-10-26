# Product Requirements Document (PRD): StockPilot — Smart Inventory & Low-Stock Alert System

> **Agent Execution Directive (For Antigravity / AI Coding Assistant):**
> Read this entire specification carefully and build the complete, production-ready mini-project end-to-end. Replace the legacy Flask implementation mentioned in initial concepts with **FastAPI** while strictly preserving all endpoints, port mappings (`5000`), SQLite volume paths (`/app/data/stockpilot.db`), Docker commands, UI capabilities, and SLA/TTR benchmarking tools. Do not leave placeholder code—implement all files completely.

---

## 1. Project Overview & Objectives
* **Project Name:** StockPilot — Smart Inventory & Low-Stock Alert System
* **Domain:** Retail and E-Commerce Inventory Operations
* **Target Users:** Small-store owners, warehouse managers, and retail inventory operators.
* **Problem Statement:** Small retailers relying on manual spreadsheets suffer from outdated stock counts after sales/restocking, missed low-stock items until customers request them, lack of clear replenishment priority, and poor multi-user visibility.
* **Proposed Solution:** A centralized, containerized FastAPI web application and dashboard that tracks product quantities by SKU and category, enforces configurable reorder thresholds, displays real-time low-stock alerts when $\text{quantity} \le \text{reorder\_level}$, persists data across container restarts using a Docker volume, exposes a `/health` endpoint for cloud monitoring, and includes automated SLA/TTR verification scripts.

---

## 2. Technology Stack
* **Backend Framework:** **FastAPI** (Python 3.11+)
* **ASGI Server:** **Uvicorn** (configured to run on host `0.0.0.0` and port `5000` for compatibility with required Docker presentation commands)
* **Database & Persistence:** **SQLite3** (stored at `/app/data/stockpilot.db` inside the container, mounted via Docker named volume `stockpilot-data`)
* **Data Validation & ORM:** **Pydantic v2** + standard `sqlite3` (or `SQLAlchemy` / `SQLModel`)
* **Frontend UI:** Server-rendered **Jinja2 Templates** + **Tailwind CSS (via CDN)** + **Vanilla JavaScript (Fetch API)** for a responsive, modern single-page dashboard experience with both form fallback and dynamic API interactions.
* **Containerization:** **Docker** (`Dockerfile` with native `HEALTHCHECK` and `docker-compose.yml`)
* **Cloud Target (Architecture Ready):** AWS EC2 (Compute), Amazon EBS (Block Storage), Amazon CloudWatch (Logs & Metrics), AWS IAM (Least-Privilege Roles), Amazon S3 (Optional CSV Backup/Export).

---

## 3. Target Repository Structure
The AI agent must generate the following directory and file structure:

```text
stockpilot/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point, routes, and startup lifecycle
│   ├── config.py            # Environment variables (DB_PATH, SECRET_KEY, PORT)
│   ├── database.py          # SQLite connection, table initialization, and demo seed data
│   ├── models.py            # Database helper functions / CRUD operations
│   ├── schemas.py           # Pydantic request/response schemas & validation
│   ├── templates/
│   │   └── index.html       # Responsive Dashboard UI (KPI cards, alerts, table, modals/forms)
│   └── static/
│       └── style.css        # Custom utility styles if needed
├── scripts/
│   ├── test_sla_ttr.py      # Automated benchmark for Functional, Latency (p95), Availability & Persistence
│   └── export_s3.py         # Optional utility to export inventory CSV locally or to AWS S3
├── data/                    # Local fallback directory for SQLite DB (.gitignored except .keep)
├── Dockerfile               # Production container definition exposing port 5000 + HEALTHCHECK
├── docker-compose.yml       # Local multi-feature container orchestration with named volume
├── .dockerignore
├── .env.example
├── requirements.txt         # FastAPI, Uvicorn, Jinja2, python-multipart, requests, pydantic
└── README.md                # Full setup, Docker commands, AWS deployment guide & SLA test instructions
```

---

## 4. Database Schema & Seed Data (`SQLite`)

### 4.1. Table Definition: `products`
Database file location must default to environment variable `DB_PATH` (default: `/app/data/stockpilot.db` in Docker, `./data/stockpilot.db` locally).

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | `PRIMARY KEY AUTOINCREMENT` | Unique internal product ID |
| `name` | `TEXT` | `NOT NULL` | Product display name |
| `category` | `TEXT` | `NOT NULL` | Retail category (e.g., Electronics, Beverages, Stationery) |
| `sku` | `TEXT` | `NOT NULL UNIQUE` | Unique Stock Keeping Unit code (e.g., `SKU-ELEC-001`) |
| `quantity` | `INTEGER` | `NOT NULL CHECK(quantity >= 0)` | Current stock count (cannot be negative) |
| `reorder_level` | `INTEGER` | `NOT NULL DEFAULT 10 CHECK(reorder_level >= 0)` | Threshold at or below which low-stock alert triggers |
| `updated_at` | `TIMESTAMP` | `DEFAULT CURRENT_TIMESTAMP` | Last stock modification timestamp |

### 4.2. Initial Seed Data (Auto-Populate on Empty DB)
On application startup (`lifespan` event in FastAPI), if the `products` table is empty, automatically insert 6 fictional demo retail products so the dashboard immediately demonstrates normal stock, borderline stock, and low-stock alerts:
1. **Wireless Barcode Scanner** | Category: `Electronics` | SKU: `SP-EL-101` | Quantity: `25` | Reorder Level: `10` (Healthy)
2. **Thermal Receipt Paper (Pack of 10)** | Category: `Supplies` | SKU: `SP-SU-204` | Quantity: `4` | Reorder Level: `15` (**LOW STOCK**)
3. **USB-C POS Dock** | Category: `Electronics` | SKU: `SP-EL-109` | Quantity: `8` | Reorder Level: `8` (**LOW STOCK** — exact threshold test $\text{quantity} \le \text{reorder\_level}$)
4. **Organic Arabica Coffee Beans 1kg** | Category: `Beverages` | SKU: `SP-BV-301` | Quantity: `42` | Reorder Level: `12` (Healthy)
5. **Heavy Duty Packing Tape** | Category: `Packaging` | SKU: `SP-PK-405` | Quantity: `2` | Reorder Level: `10` (**LOW STOCK**)
6. **Cardboard Shipping Boxes (Medium)** | Category: `Packaging` | SKU: `SP-PK-410` | Quantity: `60` | Reorder Level: `20` (Healthy)

---

## 5. Core Functional Requirements & API Endpoints

### 5.1. Health & Monitoring Endpoint
* **`GET /health`**
  * **Purpose:** Used by Docker `HEALTHCHECK`, AWS CloudWatch/ALB, and the TTR recovery test script.
  * **Behavior:** Executes a lightweight `SELECT 1` query against SQLite to verify both application uptime and persistent storage connectivity.
  * **Response (`200 OK`):**
    ```json
    {
      "status": "ok",
      "service": "stockpilot-fastapi",
      "database": "connected",
      "timestamp": "2026-10-26T00:00:00Z"
    }
    ```
  * **Error Response (`503 Service Unavailable`):** Returned if the SQLite database cannot be reached.

### 5.2. REST API Endpoints (`/api/...`)
1. **`GET /api/products`**
   * **Query Params:**
     * `search` (optional `str`): Filters by product `name`, `sku`, or `category` (case-insensitive).
     * `low_stock_only` (optional `bool`, default `false`): When `true`, returns only products where $\text{quantity} \le \text{reorder\_level}$.
   * **Response (`200 OK`):** Returns JSON object containing `summary` metrics (`total_products`, `total_units`, `low_stock_count`) and `items` list (each item includes computed boolean `is_low_stock: quantity <= reorder_level`).

2. **`POST /api/products`**
   * **Request Body (Pydantic validated):**
     * `name` (`str`, min length 2)
     * `category` (`str`, min length 2)
     * `sku` (`str`, auto-trimmed, uppercase)
     * `quantity` (`int`, $\ge 0$)
     * `reorder_level` (`int`, $\ge 0$)
   * **Validation Rules:**
     * Reject duplicate `sku` with `409 Conflict` and clear error message.
     * Reject negative `quantity` or `reorder_level` with `422 Unprocessable Entity` / `400 Bad Request`.
   * **Response (`201 Created`):** Newly created product object with `is_low_stock` flag.

3. **`PATCH /api/products/{product_id}/stock`** (Also support `POST /api/products/{product_id}/stock` for ease of use)
   * **Purpose:** Increase, decrease, or set stock quantity.
   * **Request Body:**
     * Supports either `delta` (`int`, e.g., `+1`, `-1`, `+10`, `-5`) OR `new_quantity` (`int`, $\ge 0$).
   * **Validation Rules:**
     * **Prevent Negative Stock:** If $\text{current\_quantity} + \text{delta} < 0$, strictly reject the update with `400 Bad Request` (`{"detail": "Stock quantity cannot be negative"}`).
   * **Response (`200 OK`):** Updated product JSON with recalculated `is_low_stock` status and updated `summary` counts.

4. **`PUT /api/products/{product_id}`**
   * **Purpose:** Update product details or `reorder_level`.

5. **`DELETE /api/products/{product_id}`**
   * **Purpose:** Delete a product from the catalog (`200 OK`).

6. **`GET /api/export/csv`**
   * **Purpose:** Downloads current inventory status as a CSV report (demonstrates readiness for optional S3 backup/export).

---

## 6. Frontend Dashboard Specification (`GET /`)

The main dashboard (`app/templates/index.html`) must be clean, modern, and screenshots-friendly for academic evaluation (Slide 12 evidence):

1. **Header Bar:**
   * Displays **"StockPilot — Smart Inventory & Low-Stock Alert System"** logo/badge.
   * Live **System Health Indicator Badge** (polls `/health` every 10 seconds and shows `Status: OK (Healthy)` in green or `Unreachable` in red).
   * Quick button to view raw `/health` JSON, `/docs` (FastAPI Swagger UI), and `Export CSV`.

2. **KPI Summary Cards (Top Row):**
   * **Total Products:** Count of unique SKUs in catalog.
   * **Total Inventory Units:** Sum of `quantity` across all products.
   * **Low-Stock Alerts:** Count of products where $\text{quantity} \le \text{reorder\_level}$ (highlighted in amber/red when $> 0$).

3. **Global Low-Stock Alert Banner:**
   * Immediately visible at the top of the workspace whenever 1 or more products have $\text{quantity} \le \text{reorder\_level}$.
   * Lists the count of affected items and includes a **"Filter Low-Stock Items"** quick-toggle button.

4. **Add Product Panel / Modal:**
   * Inputs: Product Name, Category, Unique SKU, Initial Quantity ($\ge 0$), Reorder Threshold ($\ge 0$).
   * Instant validation feedback (e.g., duplicate SKU warning or negative number prevention).

5. **Interactive Inventory Table:**
   * **Search & Filter Controls:** Search input (by Name/SKU/Category) + "Show Low-Stock Only" toggle switch.
   * **Columns:** SKU, Product Name, Category, Current Quantity, Reorder Threshold, Status Badge, Quick Actions.
   * **Status Badge:**
     * Red/Amber pulsing badge `LOW STOCK (Reorder Needed)` when $\text{quantity} \le \text{reorder\_level}$ (or `OUT OF STOCK` when $\text{quantity} == 0$).
     * Green badge `IN STOCK` when $\text{quantity} > \text{reorder\_level}$.
   * **Quick Stock Update Controls:**
     * `-1` button (disabled or shows toast error if quantity is `0` to demonstrate negative stock prevention).
     * `+1` button and `+10` restock button.
     * Custom quantity adjustment input.

---

## 7. Docker & Containerization Requirements

To align strictly with Slide 7 of the project presentation, the Docker setup **must** adhere to these exact specifications:

### 7.1. `Dockerfile` Requirements
* Base Image: `python:3.11-slim`
* Working Directory: `/app`
* Create persistent data mount directory `/app/data` with appropriate permissions.
* Environment variables:
  * `PYTHONUNBUFFERED=1`
  * `DB_PATH=/app/data/stockpilot.db`
  * `PORT=5000`
* Expose port `5000`.
* Native Docker `HEALTHCHECK`:
  ```dockerfile
  HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health').read()" || exit 1
  ```
* Startup command:
  ```dockerfile
  CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5000"]
  ```

### 7.2. Required Starter Commands Compatibility
The project **must** build and run seamlessly using the exact commands printed in the presentation:
```bash
docker build -t stockpilot:1.0 .
docker run -p 5000:5000 -v stockpilot-data:/app/data stockpilot:1.0
```

---

## 8. SLA, Performance & TTR Benchmarking Script (`scripts/test_sla_ttr.py`)

A core requirement of the rubric (Slides 8, 9, 10, and 13) is experimentally measuring and recording **Response Time ($p95$)**, **Availability**, **Data Persistence (RPO)**, and **Time to Recover (TTR)**.

Create a standalone Python CLI tool `scripts/test_sla_ttr.py` with subcommands or an interactive menu that executes and prints formatted tables ready for the presentation:

1. **Functional & Persistence Verification Test:**
   * Creates or updates a test SKU (`SKU-TEST-PERSIST`), records its quantity, prompts or automatically checks after container restart that the exact quantity survived in the `stockpilot-data` volume.
2. **Latency & SLA Benchmark ($p95 < 2\text{ seconds}$ target):**
   * Sends a controlled batch of 100 requests to `GET /api/products` and `GET /health`.
   * Computes and displays Min, Average, Median ($p50$), and $p95$ response times in milliseconds/seconds.
   * Evaluates PASS/FAIL against the SLA target ($p95 < 2.0\text{s}$).
3. **Availability Benchmark ($\ge 99\%$ target):**
   * Runs health checks over a configurable test window, calculates:
     $$\text{Availability (\%)} = \left(\frac{\text{Successful Checks}}{\text{Total Checks}}\right) \times 100\%$$
4. **Interactive Failure & TTR Experiment Mode (`--measure-ttr`):**
   * **Step 1 (Baseline):** Verifies `/health` returns `200 OK`.
   * **Step 2 (Failure Detection):** Polls `/health` every 0.5s. When the user stops the container (`docker stop <container>`), records exact `incident_detection_time` ($T_{\text{detect}}$) when `/health` fails.
   * **Step 3 (Recovery Verification):** Continues polling while the user restarts the container (`docker start <container>`). As soon as `/health` returns `200 OK` and verifies database persistence, records `restoration_verification_time` ($T_{\text{restore}}$).
   * **Step 4 (Compute TTR):** Calculates:
     $$\text{TTR} = T_{\text{restore}} - T_{\text{detect}}$$
     Prints exact timestamps and evaluates against the target ($\text{TTR} < 120\text{ seconds}$).

---

## 9. Security, Cost & Documentation (`README.md`)

The generated `README.md` must include comprehensive documentation covering the evaluation checklist:
1. **Local & Docker Quickstart** (exact commands for build, volume creation, run, stop, and logs).
2. **End-to-End Cloud Architecture Diagram** (ASCII/Mermaid diagram showing Browser $\rightarrow$ AWS EC2 $\rightarrow$ Docker Engine $\rightarrow$ FastAPI Container + `/health` + Named Volume on Amazon EBS $\rightarrow$ CloudWatch Logs/Metrics & S3 Exports).
3. **AWS Deployment & Security Guide:**
   * EC2 Security Group rules (restrict inbound to port `22`/`80`/`5000`).
   * IAM Least-Privilege Role configuration for CloudWatch and S3.
   * Environment variable management (`SECRET_KEY`, no hardcoded AWS credentials).
   * Resource cleanup checklist to prevent unwanted billing after demo completion.
4. **Step-by-Step Demo & Screenshot Guide:** Instructions on how to capture the 6 required presentation screenshots (Dashboard, Alert Behavior, `/health` Endpoint, Docker Container/Logs, Recovery TTR Experiment, and Benchmark Results Table).

---

## 10. Acceptance Criteria for Code Generation
- [ ] Application runs with zero errors via `uvicorn app.main:app --port 5000` locally and via `docker build -t stockpilot:1.0 .` & `docker run -p 5000:5000 -v stockpilot-data:/app/data stockpilot:1.0`.
- [ ] Negative stock quantities are strictly prevented at both the API (HTTP 400/422) and UI levels.
- [ ] Low-stock alerts trigger accurately whenever $\text{quantity} \le \text{reorder\_level}$.
- [ ] SQLite database persists across container stop/remove/start cycles when using `-v stockpilot-data:/app/data`.
- [ ] FastAPI automatic OpenAPI documentation is accessible at `/docs` alongside the custom dashboard at `/` and health check at `/health`.
- [ ] `scripts/test_sla_ttr.py` runs cleanly and outputs a complete Markdown summary table of all SLA/TTR metrics for Slide 10 and Slide 13.