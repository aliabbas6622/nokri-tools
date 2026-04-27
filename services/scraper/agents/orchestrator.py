"""
Orchestrator Module (v3)
Advanced pipeline with ATS routing and content-aware deduplication.
"""

import time
import sys
from typing import List, Dict
from services.scraper.agents import search_agent, quality_filter, scrape_agent, structure_agent, deduplicator

# Stats
ORCHESTRATOR_STATS = {
    "total_requests": 0,
    "total_jobs_found": 0,
    "avg_latency": 0
}

async def discover_jobs(query: str, location: str, limit: int = 20) -> List[Dict]:
    start_time = time.time()
    ORCHESTRATOR_STATS["total_requests"] += 1

    print(f"Discovery v3: {query} @ {location}")

    try:
        # 1. Search & Tag
        tagged_urls = await search_agent.search(query, location, limit * 3)

        # 2. Rank & Preliminary Filter
        scored_urls = quality_filter.filter_and_rank(tagged_urls, limit * 2)

        # 3. Hybrid Scraping (ATS API > JobSpy > Fallback)
        # 3A. JobSpy
        jobspy_results = await scrape_agent.scrape_structured(query, location, limit)

        # 3B. Unstructured (Career pages + ATS APIs)
        unstructured_urls = [u for u in scored_urls if not u["is_structured"]]
        sgai_raw_results = await scrape_agent.scrape_unstructured(unstructured_urls)

        # 4. Intelligent Structuring (LLM only for messy data)
        structured_sgai = await structure_agent.structure(sgai_raw_results)

        # 5. Advanced Deduplication (MinHash)
        all_jobs = jobspy_results + structured_sgai
        unique_jobs = deduplicator.deduplicate_content(all_jobs)

        # 6. Final Ranking
        sorted_jobs = sorted(unique_jobs, key=lambda x: x.get("source_score", 0), reverse=True)
        final_list = sorted_jobs[:limit]

        latency = time.time() - start_time
        ORCHESTRATOR_STATS["total_jobs_found"] += len(final_list)
        ORCHESTRATOR_STATS["avg_latency"] = (
            (ORCHESTRATOR_STATS["avg_latency"] * (ORCHESTRATOR_STATS["total_requests"] - 1) + latency)
            / ORCHESTRATOR_STATS["total_requests"]
        )

        return final_list

    except Exception as e:
        print(f"Orchestrator v3 Error: {str(e)}", file=sys.stderr)
        return []
