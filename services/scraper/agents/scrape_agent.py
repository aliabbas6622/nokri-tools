"""
Scraping Agent Module (v2)
Handles structured (JobSpy) and unstructured (ScrapeGraphAI) scraping paths.
"""

import os
import sys
import asyncio
from typing import List, Dict
from jobspy import scrape_jobs
from scrapegraphai.graphs import SmartScraperGraph

async def scrape_structured(query: str, location: str, limit: int) -> List[Dict]:
    """
    PATH A: Uses JobSpy to fetch structured job listings.
    """
    print(f"PATH A: Scraping structured sources for {query} in {location}")
    try:
        # jobspy is synchronous, run it in a thread
        loop = asyncio.get_event_loop()
        df = await loop.run_in_executor(None, lambda: scrape_jobs(
            site_name=["indeed", "linkedin", "glassdoor"],
            search_term=query,
            location=location,
            results_wanted=limit,
            hours_old=720, # 30 days
            country_indeed="USA" # Default, maybe adjust later
        ))

        if df is None or df.empty:
            return []

        # Convert DataFrame to list of dicts and map to our schema
        jobs = []
        for _, row in df.iterrows():
            jobs.append({
                "title": str(row.get("title", "")),
                "company": str(row.get("company", "")),
                "location": str(row.get("location", "")),
                "salary_min": row.get("min_amount") if row.get("min_amount") else None,
                "salary_max": row.get("max_amount") if row.get("max_amount") else None,
                "salary_currency": str(row.get("currency", "")) if row.get("currency") else None,
                "job_type": str(row.get("job_type", "")) if row.get("job_type") else None,
                "jd_text": str(row.get("description", "")),
                "apply_url": str(row.get("job_url", "")),
                "date_posted": str(row.get("date_posted", "")) if row.get("date_posted") else None,
                "source": str(row.get("site", "jobspy")),
                "source_score": 80, # TIER_2 default for job boards
                "is_already_structured": True
            })
        return jobs
    except Exception as e:
        print(f"Error in JobSpy scraping: {str(e)}", file=sys.stderr)
        return []

async def scrape_unstructured_single(url_obj: Dict) -> Dict:
    """Scrapes a single unstructured URL using ScrapeGraphAI."""
    url = url_obj["url"]
    print(f"PATH B: Scraping unstructured source: {url}")

    graph_config = {
        "llm": {
            "api_key": os.getenv("GEMINI_API_KEY"),
            "model": "gemini/gemini-2.0-flash",
        },
        "verbose": False,
        "headless": True,
    }

    try:
        scraper = SmartScraperGraph(
            prompt="""Extract job listing data and return as JSON with these exact fields:
            title, company, location, salary_min, salary_max, salary_currency, job_type, jd_text, apply_url, date_posted.
            Return null for missing fields.""",
            source=url,
            config=graph_config
        )

        # SmartScraperGraph.run() is synchronous
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, scraper.run)

        if result:
            result["source"] = url
            result["source_score"] = url_obj.get("score", 100)
            result["is_already_structured"] = False
            return result
        return None
    except Exception as e:
        print(f"Error in ScrapeGraphAI for {url}: {str(e)}", file=sys.stderr)
        return None

async def scrape_unstructured(unstructured_urls: List[Dict]) -> List[Dict]:
    """
    PATH B: Uses ScrapeGraphAI to fetch data from company pages.
    """
    semaphore = asyncio.Semaphore(5)

    async def sem_scrape(url_obj):
        async with semaphore:
            return await scrape_unstructured_single(url_obj)

    tasks = [sem_scrape(u) for u in unstructured_urls]
    results = await asyncio.gather(*tasks)
    return [r for r in results if r is not None]
