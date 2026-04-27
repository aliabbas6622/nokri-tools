"""
Search Agent Module (v2-hardened)
Searches for job listing URLs with exponential backoff, User-Agent rotation, and caching.
"""

import asyncio
import random
import sys
import urllib.parse
import time
from typing import List, Dict, Optional
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
]

STRUCTURED_SOURCES = ["indeed", "linkedin", "glassdoor", "ziprecruiter"]
UNSTRUCTURED_SOURCES = ["greenhouse", "lever", "ashby", "workday", "smartrecruiters", "wellfound"]

# Simple in-memory cache: hash(query+location) -> {timestamp, results}
SEARCH_CACHE = {}
CACHE_TTL = 3600 # 1 hour

def get_source_and_structure(url: str) -> Dict[str, any]:
    """Identifies the source and whether it is structured."""
    url_lower = url.lower()
    source = "unknown"

    for s in STRUCTURED_SOURCES + UNSTRUCTURED_SOURCES:
        if s in url_lower:
            source = s
            break

    is_structured = source in STRUCTURED_SOURCES
    return {"source": source, "is_structured": is_structured}

async def fetch_with_retry(crawler, url, query_text, max_retries=3):
    """Fetches a URL with exponential backoff and rotating User-Agents."""
    for attempt in range(max_retries):
        try:
            user_agent = random.choice(USER_AGENTS)
            config = CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                user_agent=user_agent
            )

            result = await crawler.arun(url=url, config=config)

            found_links = []
            if result.success:
                links = result.links.get("internal", []) + result.links.get("external", [])
                for link in links:
                    href = link.get("href", "")
                    if href.startswith("https://") and "google.com" not in href and "bing.com" not in href:
                        found_links.append(href)

                if not found_links and ("detected unusual traffic" in result.html.lower() or "blocked" in result.html.lower()):
                    raise Exception("Anti-bot detected")

                return found_links
            else:
                raise Exception(f"Crawl failed: {result.error_message}")

        except Exception as e:
            wait_time = (2 ** attempt) + random.random()
            print(f"Attempt {attempt+1} failed for {query_text}: {str(e)}. Retrying in {wait_time:.2f}s...", file=sys.stderr)
            await asyncio.sleep(wait_time)

    return []

async def search(query: str, location: str, limit: int = 50) -> List[Dict]:
    """
    Searches for job listing URLs with caching and resilience.
    """
    cache_key = f"{query.lower()}:{location.lower()}"
    now = time.time()

    if cache_key in SEARCH_CACHE:
        cache_entry = SEARCH_CACHE[cache_key]
        if now - cache_entry["timestamp"] < CACHE_TTL:
            print(f"Search cache hit for: {cache_key}")
            return cache_entry["results"]

    search_queries = [
        f"{query} {location} jobs site:greenhouse.io",
        f"{query} {location} site:lever.co",
        f"{query} {location} site:ashbyhq.com",
        f"{query} {location} site:linkedin.com/jobs",
        f"{query} {location} site:indeed.com/viewjob",
        f"{query} {location} site:wellfound.com/jobs",
        f"{query} {location} jobs apply 2026",
    ]

    all_tagged_urls = []
    seen_urls = set()

    async with AsyncWebCrawler(verbose=False) as crawler:
        for q in search_queries:
            if len(all_tagged_urls) >= 50:
                break

            encoded_query = urllib.parse.quote(q)
            google_url = f"https://www.google.com/search?q={encoded_query}"

            found_links = await fetch_with_retry(crawler, google_url, q)

            # Fallback to Bing if Google returned nothing
            if not found_links:
                print(f"Google failed for '{q}', trying Bing fallback...", file=sys.stderr)
                bing_url = f"https://www.bing.com/search?q={encoded_query}"
                found_links = await fetch_with_retry(crawler, bing_url, f"BING:{q}")

            for url in found_links:
                if url not in seen_urls:
                    tag_info = get_source_and_structure(url)
                    all_tagged_urls.append({
                        "url": url,
                        **tag_info
                    })
                    seen_urls.add(url)

            await asyncio.sleep(1)

    results = all_tagged_urls[:50]
    SEARCH_CACHE[cache_key] = {"timestamp": now, "results": results}
    return results
