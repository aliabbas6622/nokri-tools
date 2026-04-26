"""
Orchestrator Module (v2)
Connects all stages with the two-path (Structured vs Unstructured) architecture.
"""

from typing import List, Dict
from services.scraper.agents import search_agent, quality_filter, scrape_agent, structure_agent

async def discover_jobs(
    query: str,
    location: str,
    limit: int = 20
) -> List[Dict]:
    """
    Orchestrates the upgraded job discovery pipeline.
    """
    print(f"Starting discovery (v2) for: {query} in {location}")

    # Stage 1 — find URLs + tag structured/unstructured
    tagged_urls = await search_agent.search(query, location, limit * 3)
    print(f"Stage 1: Found {len(tagged_urls)} tagged URLs")

    # Stage 2 — score, rank, filter, remove ghost jobs
    scored_urls = quality_filter.filter_and_rank(tagged_urls, limit * 2)
    print(f"Stage 2: Kept {len(scored_urls)} high-quality URLs")

    # Split by path
    # Note: Stage 1 tags them, but Stage 3 handles the actual scraping.
    # JobSpy handles its own search+scrape for structured sources.
    # ScrapeGraphAI handles specific unstructured URLs.

    unstructured_urls = [u for u in scored_urls if not u["is_structured"]]

    # Stage 3A — JobSpy for structured (fast, no LLM)
    jobspy_results = await scrape_agent.scrape_structured(query, location, limit)
    print(f"Stage 3A: JobSpy found {len(jobspy_results)} jobs")

    # Stage 3B — ScrapeGraphAI for unstructured
    sgai_raw_results = await scrape_agent.scrape_unstructured(unstructured_urls)
    print(f"Stage 3B: ScrapeGraphAI scraped {len(sgai_raw_results)} jobs")

    # Stage 4 — Structure agent (PATH B only)
    structured_sgai = await structure_agent.structure(sgai_raw_results)
    print(f"Stage 4: Structured {len(structured_sgai)} unstructured jobs")

    # Merge, deduplicate, sort by score
    all_jobs = jobspy_results + structured_sgai

    deduped = deduplicate_by_company_role(all_jobs)
    sorted_jobs = sort_by_score(deduped)

    print(f"Final: Returning {min(len(sorted_jobs), limit)} jobs after deduplication and sorting")
    return sorted_jobs[:limit]

def deduplicate_by_company_role(jobs: List[Dict]) -> List[Dict]:
    """Removes duplicate company+title combinations."""
    seen = set()
    unique = []
    for job in jobs:
        company = str(job.get("company", "")).lower()
        title = str(job.get("title", "")).lower()
        key = f"{company}_{title}"
        if key not in seen:
            seen.add(key)
            unique.append(job)
    return unique

def sort_by_score(jobs: List[Dict]) -> List[Dict]:
    """Sorts jobs by source_score descending."""
    return sorted(
        jobs,
        key=lambda x: x.get("source_score", 0),
        reverse=True
    )
