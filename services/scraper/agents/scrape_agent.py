"""
Scraping Agent Module (v3)
Handles structured (JobSpy), ATS API routing, and fallback unstructured scraping.
"""

import os
import sys
import asyncio
from typing import List, Dict, Optional
from jobspy import scrape_jobs
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode
from services.scraper.agents import ats_router

async def scrape_structured(query: str, location: str, limit: int) -> List[Dict]:
    """PATH A: JobSpy."""
    print(f"PATH A: JobSpy search for {query} in {location}")
    try:
        loop = asyncio.get_event_loop()
        df = await asyncio.wait_for(
            loop.run_in_executor(None, lambda: scrape_jobs(
                site_name=["indeed", "linkedin", "glassdoor"],
                search_term=query,
                location=location,
                results_wanted=limit,
                hours_old=720,
                country_indeed="USA"
            )),
            timeout=20.0
        )
        if df is None or df.empty: return []
        jobs = []
        for _, row in df.iterrows():
            jobs.append({
                "title": str(row.get("title", "")),
                "company": str(row.get("company", "")),
                "location": str(row.get("location", "")),
                "jd_text": str(row.get("description", "")),
                "apply_url": str(row.get("job_url", "")),
                "date_posted": str(row.get("date_posted", "")) if row.get("date_posted") else None,
                "source": str(row.get("site", "jobspy")),
                "source_score": 80,
                "is_already_structured": True
            })
        return jobs
    except Exception as e:
        print(f"JobSpy Error: {str(e)}", file=sys.stderr)
        return []

async def scrape_unstructured_single(url_obj: Dict, crawler: AsyncWebCrawler) -> Optional[Dict]:
    """PATH B: ATS Router -> Scrape Fallback."""
    url = url_obj["url"]

    # 1. Try ATS API Router first (v3 improvement)
    ats_data = await ats_router.route_ats(url)
    if ats_data:
        print(f"ATS API Hit: {url}")
        ats_data["source_score"] = url_obj.get("score", 100)
        ats_data["is_already_structured"] = True
        return ats_data

    # 2. Fallback to Crawl4AI (cheaper than ScrapeGraphAI)
    print(f"PATH B: Fallback scrape for {url}")
    try:
        config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)
        result = await asyncio.wait_for(crawler.arun(url=url, config=config), timeout=15.0)
        if result.success:
            return {
                "title": None, # Will be filled by Stage 4
                "company": None,
                "location": None,
                "jd_text": result.markdown or result.html,
                "apply_url": url,
                "date_posted": None,
                "source": url,
                "source_score": url_obj.get("score", 100),
                "is_already_structured": False
            }
    except Exception as e:
        print(f"Fallback Error for {url}: {str(e)}", file=sys.stderr)
    return None

async def scrape_unstructured(unstructured_urls: List[Dict]) -> List[Dict]:
    """Orchestrates Path B scraping."""
    semaphore = asyncio.Semaphore(5)
    async with AsyncWebCrawler(verbose=False) as crawler:
        async def sem_scrape(u):
            async with semaphore: return await scrape_unstructured_single(u, crawler)
        tasks = [sem_scrape(u) for u in unstructured_urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
    return [r for r in results if isinstance(r, dict)]
