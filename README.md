# 🚀 AstraChain — Autonomous AI Supply Chain & Multi-Agent Logistics Engine

[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18.2-61DAFB.svg?style=flat&logo=react&logoColor=black)](https://react.dev)
[![Vite](https://img.shields.io/badge/Vite-5.0+-646CFF.svg?style=flat&logo=vite&logoColor=white)](https://vitejs.dev)
[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**AstraChain** is a next-generation, autonomous supply chain operating system powered by multi-agent AI. Built for enterprise retail and FMCG logistics (demonstrated on the **Rio Mart Unified Dataset** with 280,000+ transaction records), AstraChain orchestrates inventory intelligence, festival-wise demand forecasting, perishable shelf-life expiry tracking, live Google Maps route optimization with real-time highway traffic telemetry, a live notification hub, and lock-screen mobile phone alerts.

---

## 🌟 Key Features

- **🤖 Multi-Agent Orchestrator**: Synchronous and background sub-agents (`DataAgent`, `InventoryAgent`, `ForecastAgent`, `WastageAgent`, `RouteAgent`) that coordinate autonomous reordering and supply decisions.
- **⚡ 1-Click Operational Actions**:
  - **1-Click Restock**: Instantly resolves stockout risk and updates warehouse safety thresholds.
  - **1-Click Festival Pre-Stock**: Automatically calculates and allocates holiday surge buffers (Diwali, Holi, Eid, Christmas, etc.).
  - **1-Click Expiry Mitigation**: Flags perishable items within 5 days of expiry and initiates volume promotional markdowns.
  - **1-Click Delivery Confirmation**: Dispatches delivery arrival notifications with fuel and CO₂ savings metrics.
- **🔔 Live Real-Time Notification Hub**:
  - Live WebSocket stream delivering single-block floating toast cards with synthesized Web Audio chimes.
  - Reactive Navbar Bell icon with dynamic unread badge counter, pulsing glow, and live categorization filters.
- **📱 Lock-Screen Mobile Phone Alerts**:
  - Real-time native push notifications delivered directly to iOS and Android lock screens via **NTFY** and **Telegram Bot**.
  - Includes interactive 1-click action buttons on phone notifications (`[View Restocked Inventory]`, `[1-Click Reorder]`, `[Track Route]`).
- **🗺️ Live Route Optimization Agent**:
  - Integrated 2-Opt and TSP route solvers, live Google Maps view, interactive satellite and dark HUD modes.
  - Highway traffic congestion overlays, toll plazas, real-time fleet GPS tracking, turn-by-turn navigation drawer, and diesel economics / ESG CO₂ abatement telemetry.
- **📊 Rio Mart Unified Dataset Integration**: Automatically seeds 969 catalog products, warehouses, suppliers, and 90 days of sales history upon startup.
- **🌓 Dark / Light Mode Toggle**: Seamless zero-flicker UI theming persisted across sessions.

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    AstraChain Dashboard                     │
│        (React 18 + Vite + Tailwind CSS + Recharts)          │
└──────────────┬──────────────────────────────▲───────────────┘
               │ HTTP REST API                │ WebSocket /ws
               ▼                              │ (Live Events)
┌─────────────────────────────────────────────┴───────────────┐
│                   FastAPI Backend Core                      │
│     app.main:app · SQLAlchemy 2.0 ORM · Pydantic v2        │
├─────────────────────────────────────────────────────────────┤
│  Agents & Services:                                         │
│  ├─ Multi-Agent Orchestrator                                │
│  ├─ Festival Forecast Engine (20+ Indian & Global Events)   │
│  ├─ Inventory & Stockout Safety Threshold Manager           │
│  ├─ Perishable Shelf-Life & Expiry Clearance Agent          │
│  └─ Route Optimization (2-Opt TSP + ESG Telemetry)          │
├─────────────────────────────────────────────────────────────┤
│  Persistence:                                               │
│  ├─ SQLite (Zero-config local) / PostgreSQL                 │
│  └─ In-Memory Pipeline State & Seeding (Rio Mart Dataset)   │
└──────────────┬──────────────────────────────┬───────────────┘
               ▼                              ▼
     [NTFY Phone Push]              [Telegram Bot Webhook]
 (https://ntfy.sh/topic)            (Mobile Notifications)
```

---

## 📋 Prerequisites

Ensure you have the following installed on your machine:
- **Node.js**: v18.0.0 or higher ([Download Node.js](https://nodejs.org/))
- **Python**: 3.10, 3.11, 3.12, or 3.13 ([Download Python](https://www.python.org/))
- **Git**: ([Download Git](https://git-scm.com/))

---

## 🚀 Quick Start Guide (How to Run)

### 1. Clone the Repository

```bash
git clone https://github.com/Tanishagit29/AstraChain_final.git
cd AstraChain_final
```

---

### 2. Backend Setup & Run (FastAPI)

Open a terminal window:

```bash
# Navigate to backend folder
cd backend

# Create Python virtual environment
# Windows:
python -m venv venv
.\venv\Scripts\activate

# macOS / Linux:
python3 -m venv venv
source venv/bin/activate

# Install required Python packages
pip install -r requirements.txt

# (Optional) Copy environment file
# By default, zero-configuration SQLite is used automatically
copy .env.example .env     # Windows
cp .env.example .env       # macOS / Linux

# Start the FastAPI backend server
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

> **Backend is now live at:**
> - **API URL**: `http://localhost:8000`
> - **Interactive Swagger Docs**: `http://localhost:8000/docs`
> - **Alternative Redoc**: `http://localhost:8000/redoc`

*Note: On initial startup, the backend automatically seeds the Rio Mart dataset into SQLite (`astrachain.db`).*

---

### 3. Frontend Setup & Run (Vite + React)

Open a **second terminal window**:

```bash
# From the project root (where package.json is located)
cd AstraChain_final

# Install dependencies
npm install

# Start Vite development server
npm run dev
```

> **Frontend is now live at:**
> - **Web App**: `http://localhost:5173`

Open your browser and navigate to **`http://localhost:5173`** to access the AstraChain operational suite.

---

## 📱 Setting Up Mobile Phone Alerts (NTFY)

AstraChain delivers real-time lock-screen notifications for stockouts, restocks, festival surges, and delivery arrivals directly to your mobile phone:

1. **Option A — Web / Mobile Browser (No App Needed)**:
   - Visit **[https://ntfy.sh/astrachain-daksh-alert](https://ntfy.sh/astrachain-daksh-alert)** on your smartphone.
   - Tap **Subscribe** and enable browser notifications.

2. **Option B — Native Mobile App (Recommended)**:
   - Install **ntfy** from the [Google Play Store](https://play.google.com/store/apps/details?id=io.heckel.ntfy) or [Apple App Store](https://apps.apple.com/app/ntfy/id1625396347).
   - Tap **+** (Add subscription) and enter topic: `astrachain-daksh-alert`.

3. **Verify with Live Test**:
   - In the AstraChain web app, click the **Notification Bell** icon in the navbar.
   - Click the **Phone Alerts (📱)** button.
   - Click **Send Test Alert to Phone** to see an instant notification appear on your lock screen.

---

## 🧭 Key Application Views & Workflows

| Page Route | Purpose & 1-Click Operations |
|---|---|
| `/` | **Operations Executive Dashboard**: Real-time sales, inventory safety levels, critical stockout cards, and agent status. |
| `/inventory` | **Inventory Intelligence**: Multi-warehouse stock tracking, stockout ratio charts, and **1-Click Reorder** / **1-Click Reorder All**. |
| `/demand-forecast` | **Festival Item Demand Predictor**: Predicts peak item-level demand for 20+ festivals (Diwali, Holi, Eid, Christmas, etc.) with **1-Click Pre-Stock Buffers**. |
| `/wastage` | **Automation & Expiry Agent**: Perishable shelf-life monitoring, near-expiry graph (≤5 days), and **1-Click Mitigate** volume markdowns. |
| `/routes` | **Route Optimization Agent**: Fleet GPS tracking, 2-Opt TSP optimization, Google Maps embed, highway traffic flow, fuel saved (₹), and **Items Reached** delivery confirmation. |
| `/copilot` | **Multi-Agent AI Copilot**: Interactive conversational assistant with direct database telemetry fallback and Groq LLaMA integration. |

---

## 🧪 Running Tests & Production Builds

### Backend Integration Tests

```bash
cd backend
pytest -v
```

All integration test suites test agent workflows, 1-click execution endpoints, database models, and notification streaming.

### Frontend Production Build

```bash
# Inside project root
npm run build
```

Builds optimized production assets to `/dist` using Vite.

---

## ⚙️ Environment Variables (`backend/.env`)

| Variable | Description | Default |
|---|---|---|
| `DATABASE_URL` | SQLite or PostgreSQL connection string | `sqlite:///./astrachain.db` |
| `SECRET_KEY` | JWT authorization signing secret | `astrachain-super-secret-key...` |
| `CORS_ORIGINS` | Permitted client origins | `["http://localhost:5173", ...]` |
| `GROQ_API_KEY` | Optional Groq Cloud API key for LLaMA 3.3 | *(Optional, graceful DB fallback included)* |
| `GROQ_MODEL` | Target Groq LLM model | `llama-3.3-70b-versatile` |

---

## 🛠️ Tech Stack

- **Frontend**: React 18, Vite 5, Tailwind CSS, Recharts, Lucide React, Web Audio API.
- **Backend**: FastAPI, Uvicorn, Python 3.12+, Pydantic v2, SQLAlchemy 2.0, Alembic, Pandas.
- **Real-Time & Push**: WebSockets, NTFY Push API, Telegram Bot API.
- **Algorithms**: 2-Opt Traveling Salesperson Problem (TSP), Haversine Geo-distance, Exponential Moving Average (EMA).

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
