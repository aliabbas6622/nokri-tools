# Nokri Job Discovery Agent (v2)

This service is a standalone Python module designed to discover job listings from various web sources. It uses a 4-stage pipeline to search, filter, scrape, and structure job data.

## Features (v2)
- **Two-Path Scraping**:
  - **Path A (Structured)**: Uses `JobSpy` to fetch already structured data from major job boards (Indeed, LinkedIn, Glassdoor). This covers ~90% of listings and uses zero LLM tokens.
  - **Path B (Unstructured)**: Uses `ScrapeGraphAI` and `Gemini 2.0 Flash` to scrape and structure data from direct company career pages (Greenhouse, Lever, etc.).
- **Token Efficiency**: Reduces token usage by ~90% compared to v1 through DOM pruning and TOON compression.
- **Accuracy**: Uses the `instructor` library for guaranteed JSON output schema.
- **Freshness**: Automatically filters out "ghost jobs" older than 30 days.
- **Token Tracking**: Real-time monitoring of LLM usage and costs.

## 4-Stage Pipeline
1. **Search Agent**: Searches Google and Bing with smart queries and tags URLs as structured or unstructured.
2. **Quality Filter**: Scores sources by tier and freshness. Discards jobs older than 30 days.
3. **Scraping Agent**:
   - Path A: Direct extraction via JobSpy.
   - Path B: Intelligent scraping via ScrapeGraphAI.
4. **Structure Agent**:
   - Path A jobs skip this stage.
   - Path B jobs undergo DOM pruning, TOON compression, and LLM-based extraction using `instructor`.

## Setup and Installation

1. **Install Dependencies**:
   ```bash
   pip install -r services/scraper/requirements.txt
   python3 -m playwright install chromium
   ```

2. **Environment Variables**:
   Create a `.env` file in the project root:
   ```env
   GEMINI_API_KEY=your_gemini_api_key_here
   LITELLM_LOG=ERROR
   PORT=8000
   ```

3. **Run the Service**:
   ```bash
   export PYTHONPATH=$PYTHONPATH:$(pwd)
   python3 services/scraper/main.py
   ```

## Testing
Run the automated test suite:
```bash
python3 services/scraper/test_discovery.py
```

## API Endpoints

### POST /discover
Discovers jobs based on query and location.
- **Payload**: `{"query": "software engineer", "location": "Karachi", "limit": 10}`
- **Response**: List of structured job objects and token usage stats.

### GET /stats
Returns service health and cumulative token usage statistics.

### GET /health
Basic health check.

## Integration
The Next.js backend connects to this service by making POST requests to the `/discover` endpoint.
