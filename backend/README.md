# TransitOps Backend & System Guide

Production-ready FastAPI backend for **TransitOps**, an Agentic AI platform for Supply Chain Intelligence & Demand Forecasting.

---

## Technical Architecture

- **Framework:** Python 3.12 / 3.13, FastAPI, Uvicorn
- **ORM & DB:** SQLAlchemy 2.0, PostgreSQL (SQLite fallback), Alembic migrations
- **Validation:** Pydantic v2
- **Auth:** JWT tokens, bcrypt password hashing, refresh token rotation
- **Testing:** Pytest & HTTPX TestClient
- **AI Copilot & Agents:** Provider pattern (`AIProvider`), DB context retrieval, modular sub-agents (`ForecastAgent`, `InventoryAgent`, `RouteAgent`, `WastageAgent`)

---

## Step-by-Step Setup Guide

### 1. Create Virtual Environment
```bash
cd backend
python -m venv venv

# On Windows PowerShell:
.\venv\Scripts\Activate.ps1

# On Linux/macOS:
source venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables (`.env`)
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Ensure your `.env` contains:
```env
PROJECT_NAME="TransitOps API"
VERSION="1.0.0"
DATABASE_URL="sqlite:///./transitops.db" # Or "postgresql://user:password@localhost:5432/transitops"
SECRET_KEY="transitops-super-secret-key-change-in-production"
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7
CORS_ORIGINS=["http://localhost:5173", "http://127.0.0.1:5173"]
AI_PROVIDER="fallback"
```

### 4. Configure PostgreSQL / Database Migrations
Run Alembic migrations to build database tables and indexes:
```bash
alembic upgrade head
```

### 5. Seed Database
Populate realistic supply chain data (10+ categories, 30+ products, 90 days sales history, suppliers, warehouses, routes):
```bash
python -m app.database.seed
```

### 6. Start Backend Uvicorn Server
```bash
python -m uvicorn app.main:app --reload --port 8000
```
- **Health Check:** [http://localhost:8000/health](http://localhost:8000/health)
- **OpenAPI Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)

### 7. Run Pytest Test Suite
```bash
pytest -v
```

### 8. Connect React Frontend
From the root workspace directory, run Vite development server:
```bash
npm run dev
```
The React frontend at [http://localhost:5173](http://localhost:5173) connects automatically to the FastAPI backend at `http://127.0.0.1:8000/api`.

---

## API Module Map

| Module | Base Path | Description & Endpoints |
|---|---|---|
| **Health Check** | `/health` | Live status & DB connection check |
| **Auth** | `/api/auth` | `/register`, `/login`, `/refresh`, `/logout`, `/me` |
| **Dashboard** | `/api/dashboard` | `/` (Dynamic KPIs, Charts, AI Recs, Activity Logs) |
| **Inventory** | `/api/inventory` | `/`, `/{id}`, `/low-stock`, `/stockout-risk`, `/overstock-risk`, `/reorder-recommendations` |
| **Forecast** | `/api/forecast` | `/`, `/{product_id}`, `/generate` |
| **Suppliers** | `/api/suppliers` | `/`, `/{id}`, `/reliability`, `/lead-time`, `/risk` |
| **Routes** | `/api/routes` | `/`, `/{id}`, `/optimize` |
| **Wastage** | `/api/wastage` | `/`, `/near-expiry`, `/discount-recommendations`, `/expected-waste` |
| **AI Copilot** | `/api/ai` | `/chat`, `/recommendations`, `/agents` |
| **Automation** | `/api/automation` | `/rules`, `/approve`, `/reject`, `/history` |
| **Reports** | `/api/reports` | `/`, `/weekly`, `/monthly`, `/export` |
