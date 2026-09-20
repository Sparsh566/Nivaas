# Nivaas

A conversational property recommendation agent for the Indian real estate market.

Describe what you want in plain language (city, locality, budget, BHK, amenities, connectivity) and get a ranked shortlist with reasons, side-by-side comparison, and EMI estimates.

## Stack

- UI: Gradio (latest stable), mounted on FastAPI
- Backend: Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2
- Database: PostgreSQL (via docker-compose)
- LLM: Groq API with tool calling
- Web data: Tavily API for listing retrieval and locality information
- Ranking: pandas, numpy, scikit-learn, rapidfuzz

## Setup

### 1. Prerequisites

- Python 3.11+
- Docker and Docker Compose
- Groq API key (from https://console.groq.com)
- Tavily API key (from https://tavily.com, optional but recommended)

### 2. Clone and install

```bash
git clone https://github.com/Sparsh566/Nivaas.git
cd Nivaas
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/Mac:
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env and add your API keys:
# GROQ_API_KEY=your_groq_key_here
# TAVILY_API_KEY=your_tavily_key_here (optional)
```

### 4. Start PostgreSQL

```bash
docker compose up -d
```

### 5. Run database migrations

```bash
alembic upgrade head
```

### 6. Generate favicons (optional)

```bash
pip install cairosvg Pillow
python scripts/generate_favicons.py
```

### 7. Run the app

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 7860
```

Open http://localhost:7860 in your browser.

### 8. Demo mode

If you do not have a Tavily API key or want to test without using credits:

```bash
# In .env:
DEMO_MODE=true
```

This uses sample listings from `data/demo_listings.json`.

## Running tests

```bash
pytest tests/ -v
```

Tests mock all external APIs (Groq, Tavily) and never spend credits.

## Running the UI rules check

```bash
python scripts/check_ui_rules.py
```

## Project structure

```
app/
  main.py           # FastAPI entry point
  config.py          # Configuration (pydantic-settings)
  agent/             # LLM agent loop and prompts
  tools/             # Tool implementations (search, compare, EMI, etc.)
  ranking/           # Scoring engine, parsers, EMI calculator, weights
  db/                # SQLAlchemy models, engine, queries
  ui/                # Gradio Blocks app, theme, CSS, components
  legal/             # Terms and Privacy page renderers
  static/            # Favicon and static assets
tests/               # pytest test suite
scripts/             # Utility scripts (favicon gen, UI rules check)
data/                # Demo listings JSON
alembic/             # Database migrations
```

## How matching works

Each listing is scored against your requirements using these factors:

| Factor | Default weight |
|--------|---------------|
| Budget fit | 25% |
| Location match | 25% |
| Connectivity | 15% |
| Area | 10% |
| Amenities | 10% |
| Property type | 5% |
| Furnishing | 5% |
| Parking | 5% |

When a factor's data is missing for a listing, it is skipped and the remaining weights are renormalized. Say "prioritize metro" to adjust weights.

## Legal pages

- /terms: Terms of Service
- /privacy: Privacy Policy

## Known limitations

- Property portals may block or throttle web scraping, resulting in fewer listings.
- Tavily free tier allows 1,000 credits/month (40 credits/day default cap).
- Listing data depends on what portals expose in their page text.
- Distance and connectivity data is only available when mentioned on listing pages.
- The app does not have live market data; all listings come from web search at query time.
>>>>>>> 587f43a (feat: initial implementation of Nivaas conversational property recommendation agent)
