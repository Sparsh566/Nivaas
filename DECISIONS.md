# Decisions

This document records every significant design decision made during development.

## 1. Groq model selection

**Decision:** Default to `llama-3.3-70b-versatile`, read from `GROQ_MODEL` env var.

**Rationale:** Research confirmed this model supports tool calling via the OpenAI-compatible API. It is the most capable generally-available model on Groq's platform for agentic tasks.

## 2. Tavily search strategy

**Decision:** Use `search()` with `include_domains` and `include_raw_content=True`, then `extract()` for pages with insufficient text.

**Rationale:** Basic search costs 1 credit and returns page content when available. Extract costs 1 credit per 5 URLs. This minimizes credit usage on the free tier (1,000 credits/month).

## 3. Credit control

**Decision:** At most 3 Tavily calls per user message. Daily cap of 40 credits (configurable). Track in `api_usage` table.

**Rationale:** The free tier is limited. 40 credits/day allows roughly 13-20 user queries per day, sufficient for development and grading.

## 4. Listing extraction via LLM

**Decision:** Send page text to Groq with a strict schema. Grounding check in Python verifies extracted values appear in source text.

**Rationale:** The LLM is good at understanding varied page formats, but it can hallucinate. The grounding check is a deterministic safety net.

## 5. Ranking engine design

**Decision:** Deterministic weighted scoring with null-factor handling. Weights live in config. Cosine similarity only as tie-breaker.

**Rationale:** Explainability and reproducibility are essential. The user must understand why listings are ranked as they are. Random or opaque ML models would violate this.

## 6. UI framework

**Decision:** Gradio Blocks mounted on FastAPI via `gr.mount_gradio_app()`.

**Rationale:** Specified in requirements. Legal routes (`/terms`, `/privacy`) are registered on FastAPI BEFORE the Gradio mount to prevent them from being swallowed.

## 7. Gradio theme and CSS

**Decision:** Custom theme extending `gr.themes.Base` with teal accent `#1F5F5B`, small radius, system font stack. CSS hides footer and API link.

**Rationale:** Follows the visual rules: no gradients, no glassmorphism, no purple, calm editorial style.

## 8. Session state

**Decision:** `gr.State` per Gradio session. No module-level globals. State includes requirements, weights, last shortlist, conversation history.

**Rationale:** Prevents state leakage between users. Gradio's State is scoped to each browser session.

## 9. Legal pages

**Decision:** Full HTML pages served by FastAPI routes. Real content covering data practices, DPDP Act reference, Groq and Tavily disclosures.

**Rationale:** Requirements specify real legal content, not placeholders. Operator details are configurable.

## 10. Demo mode

**Decision:** `DEMO_MODE` env var (default false). When true and Tavily returns nothing, uses 12 sample listings from `data/demo_listings.json` with a visible banner.

**Rationale:** Allows testing the full pipeline without spending Tavily credits. Critical for development and grading.

## 11. Database

**Decision:** PostgreSQL via docker-compose. Three tables: `listings_cache`, `api_usage`, `locality_cache`. Alembic for migrations.

**Rationale:** Caching avoids redundant API calls. Usage tracking enforces credit limits. Async SQLAlchemy 2.0 for non-blocking operations.

## 12. Security

**Decision:** Parameterized queries only (SQLAlchemy). HTML escaping on all rendered content. URL validation (http/https only). Rate limiting. No secrets in code.

**Rationale:** Standard security practices. LLM and web content are untrusted.

## 13. Favicon

**Decision:** Hand-written SVG (house outline in accent color). Script generates ICO and PNG variants using cairosvg and Pillow.

**Rationale:** No AI-generated images. Simple geometric mark matches the design aesthetic.

## 14. EMI calculator

**Decision:** Standard amortization formula. Zero rate handled as simple division. Reference test: 50L at 8.5% for 20 years = 43,391/month.

**Rationale:** Mathematical correctness is verifiable. Labeled as an estimate throughout.

## 15. Deterministic Math & Async Engine Purity

**Decision:** Implemented vector normalization and cosine similarity tiebreaker using Python's standard `math` library. Removed unused synchronous engine instantiation in `app/db/engine.py` to maintain a pure asyncpg stack.

**Rationale:** Eliminates heavy runtime dependencies on external C-extensions for simple dot product calculations, accelerates cold import and test runtimes, and prevents unneeded synchronous database driver overhead.
