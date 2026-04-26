"""
Search Agent Module (v2)
Searches for job listing URLs and tags them with source and structure info.
"""

import asyncio
import random
import sys
import urllib.parse
from typing import List, Dict
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
]

STRUCTURED_SOURCES = ["indeed", "linkedin", "glassdoor", "ziprecruiter"]
UNSTRUCTURED_SOURCES = ["greenhouse", "lever", "ashby", "workday", "smartrecruiters", "wellfound"]

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

async def search(query: str, location: str, limit: int = 50) -> List[Dict]:
    """
    Searches for job listing URLs and tags them.
    """
    search_queries = [
        f"{query} {location} jobs site:greenhouse.io",
        f"{query} {location} site:lever.co",
        f"{query} {location} site:ashbyhq.com",
        f"{query} {location} site:linkedin.com/jobs",
        f"{query} {location} site:indeed.com/viewjob",
        f"{query} {location} site:rozee.pk",
        f"{query} {location} site:mustakbil.com",
        f"{query} {location} site:wellfound.com/jobs",
        f"{query} {location} site:remoteok.com",
        f"{query} {location} jobs apply 2026",
    ]

    all_tagged_urls = []

    async with AsyncWebCrawler(verbose=False) as crawler:
        for q in search_queries:
            if len(all_tagged_urls) >= 50:
                break

            encoded_query = urllib.parse.quote(q)
            google_url = f"https://www.google.com/search?q={encoded_query}"

            try:
                user_agent = random.choice(USER_AGENTS)
                config = CrawlerRunConfig(
                    cache_mode=CacheMode.BYPASS,
                    user_agent=user_agent
                )

                result = await crawler.arun(url=google_url, config=config)

                found_links = []
                if result.success:
                    links = result.links.get("internal", []) + result.links.get("external", [])
                    for link in links:
                        href = link.get("href", "")
                        if href.startswith("https://") and "google.com" not in href:
                            found_links.append(href)

                    if not found_links and "detected unusual traffic" in result.html.lower():
                        raise Exception("Google Blocked")
                else:
                    raise Exception("Google Failed")

                for url in found_links:
                    tag_info = get_source_and_structure(url)
                    all_tagged_urls.append({
                        "url": url,
                        **tag_info
                    })

            except Exception as e:
                print(f"Fallback to Bing for query: {q} due to {str(e)}", file=sys.stderr)
                encoded_bing = urllib.parse.quote(q)
                bing_url = f"https://www.bing.com/search?q={encoded_bing}"

                config = CrawlerRunConfig(
                    cache_mode=CacheMode.BYPASS,
                    user_agent=random.choice(USER_AGENTS)
                )
                result = await crawler.arun(url=bing_url, config=config)
                if result.success:
                    links = result.links.get("internal", []) + result.links.get("external", [])
                    for link in links:
                        href = link.get("href", "")
                        if href.startswith("https://") and "bing.com" not in href and "microsoft.com" not in href:
                            tag_info = get_source_and_structure(href)
                            all_tagged_urls.append({
                                "url": href,
                                **tag_info
                            })

            await asyncio.sleep(1)

    # Deduplicate by URL
    seen_urls = set()
    unique_tagged = []
    for item in all_tagged_urls:
        if item["url"] not in seen_urls:
            unique_tagged.append(item)
            seen_urls.add(item["url"])

    return unique_tagged[:50]
