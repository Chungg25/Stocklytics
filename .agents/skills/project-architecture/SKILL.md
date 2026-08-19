---
name: project-architecture
description: "Comprehensive guide to the Stocklytics project architecture, technologies, system design, and API structure. Use this skill when asked to explain the project, onboard new agents, or understand where to add new features/endpoints."
---

# Stocklytics Project Architecture

This skill provides a deep dive into the underlying architecture of the Stocklytics application. Read this before making structural changes to the project.

## 1. Technologies & Stack

### Frontend (User Interface)
- **Framework:** React.js powered by Vite.
- **Styling:** TailwindCSS for utility-first styling.
- **Routing:** React Router (assumed based on standard SPAs).
- **Hosting/Deployment:** Vercel (configured via Vercel Dashboard).

### Backend (API & Core Logic)
- **Framework:** FastAPI (Python 3.x).
- **Concurrency:** Uvicorn as the ASGI server.
- **Background Jobs:** APScheduler (`BackgroundScheduler`).
- **External APIs:** `yfinance` (for stock data), DuckDuckGo Search (for news), Groq & Zhipu AI (for LLM analysis).

### Database & Storage
- **Provider:** Supabase (PostgreSQL under the hood).
- **Core Tables:** `paper_portfolio`, `paper_positions`, `paper_trades`, `ai_decisions`, `ai_watchlist`.

## 2. System Design & Folder Structure

The project follows a clean **Layered Architecture** to separate concerns:

```text
Stocklytics/
├── frontend/
│   ├── src/
│   │   ├── components/    # Reusable UI elements
│   │   ├── pages/         # Page-level components (TradingViewPage, ComparePage, etc.)
│   │   └── lib/           # Utilities (e.g., supabase client wrapper)
├── backend/
│   ├── app/
│   │   ├── api/endpoints/ # API Controllers (Routing layer)
│   │   ├── ai/            # AI Decoupled Module (Clients, Prompts, Parsers)
│   │   ├── core/          # Core system setup (Scheduler configuration)
│   │   ├── repositories/  # Database access layer (Supabase Repository)
│   │   ├── services/      # Business Logic (Trading rules, Scanner, Compare, Backtest)
│   │   └── main.py        # FastAPI Application Entrypoint
```

## 3. Design Patterns Used

1. **Repository Pattern:** 
   - Found in `app/repositories/supabase_repo.py`. 
   - Abstracts all Supabase SDK calls (CRUD) away from the business logic. Prevents scattered database logic and makes it easy to switch databases or mock tests.
2. **Controller-Service Pattern:** 
   - API routes in `app/api/endpoints/` only handle HTTP requests and JSON validation. 
   - Heavy lifting is delegated to `app/services/` (e.g., `trading_logic.py`, `stock_service.py`).
3. **Decoupled AI Strategy:**
   - The AI logic is split into `llm_client.py` (API connectivity/rate limits), `prompts.py` (prompt assembly), and `parsers.py` (regex/JSON extraction). 
   - Prevents the dreaded "God Class" anti-pattern in `ai_service.py`.
4. **Observer/Scheduler Pattern:**
   - `app/core/scheduler.py` runs background threads via `APScheduler` to trigger trading jobs (every 30m) and TP/SL checks (every 1m).

## 4. API Endpoints Overview

All APIs are prefixed with `/api`.

- **Stocks (`/api/stocks`):**
  - `GET /api/stocks`: Retrieves top stocks.
  - `GET /api/benchmark`: Gets benchmark data.
  - `POST /api/scan-signals`: Runs daily trading signals scan.
  - `POST /api/compare`: Compares multiple tickers.
- **Trading & Backtest (`/api/trading`):**
  - `POST /api/trading/backtest`: Executes backtesting algorithm.
  - `GET/POST /api/trading/groups`: Manages custom stock groups via Google Sheets.
- **AI Integration (`/api/ai`):**
  - `POST /api/ai/analysis`: General stock analysis.
  - `POST /api/ai/assessment`: Generates deep investment checklist/team analysis (Streams output).
  - `POST /api/ai/intent`: Parses natural language to JSON commands.
  - `GET /api/ai/status`: Checks which AI API key is currently active.

## 5. Development Guidelines (Iron Laws)

1. **Do not inline imports:** Always import at the top of the file. Do not import services inside route functions.
2. **Never hardcode DB calls:** Any new database interaction must be added to `supabase_repo.py`.
3. **Handle Rate Limits:** AI integrations must use `execute_with_fallback()` from `llm_client.py` to auto-rotate keys on HTTP 429.
4. **Frontend API URL:** Always use ``fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/...`)`` in React to ensure Vercel production compatibility.
