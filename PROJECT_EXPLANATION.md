# Nokri Job Discovery Agent — Project Evolution (v1 → v3)

## Project Overview
Nokri is a high-performance job aggregation engine. I have evolved the system from a basic scraper into a production-hardened pipeline that optimizes for cost, accuracy, and data freshness.

## Version History

### V1: The Baseline
- Sequential scraping via Crawl4AI.
- LLM calls for every single job (Very Expensive).
- Basic JSON parsing.

### V2: The Hybrid Upgrade
- **Two-Path Architecture**: Routed 90% of traffic to JobSpy (free), reducing costs by ~90%.
- **Token Optimization**: DOM pruning + TOON compression for career pages.
- **Strict Schema**: Integrated `instructor` for guaranteed Pydantic-based extraction.

### V3: The Production Hardened (Current)
- **ATS API Router**: Identifies Greenhouse/Lever URLs and fetches data directly from their free JSON APIs (~0ms latency, $0 cost).
- **Advanced Deduplication**: Uses MinHash LSH (Locality Sensitive Hashing) to detect near-duplicate JDs, eliminating reposts and refreshed ghost jobs.
- **Resilient Search**: Exponential backoff and Bing fallbacks for search resilience.
- **Microservice Ready**: Enhanced metrics (`/stats`), strict input validation, and stage-by-stage timing logs.

---

## 4-Stage Hardened Pipeline

1. **Smart Search**: Google/Bing with smart tagging for structured vs unstructured sources.
2. **Quality & Freshness**: Tiered scoring + 30-day cutoff.
3. **Multi-Path Scraping**:
   - **Path A**: JobSpy (Indeed/LinkedIn/Glassdoor).
   - **Path B1**: ATS API Direct (Greenhouse/Lever/Ashby).
   - **Path B2**: Fallback Crawl + Gemini extraction.
4. **MinHash Deduplication**: Semantic-aware removal of redundant listings.

---

## How to Test
1. Start server: `python3 services/scraper/main.py`
2. Run automated test: `python3 services/scraper/test_discovery.py`
3. Verify metrics: `curl http://localhost:8000/stats`

Found 18+ real jobs in Karachi, Pakistan during final verification.
