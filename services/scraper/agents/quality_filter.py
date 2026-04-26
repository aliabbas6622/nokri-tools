"""
Quality Filter Agent Module (v2)
Filters and ranks job URLs with tiered scoring and freshness checks.
"""

import urllib.parse
from datetime import datetime, timezone
from typing import List, Dict, Optional
import dateutil.parser

TIER_1 = {
    "points": 100,
    "domains": [
        "greenhouse.io", "lever.co", "ashbyhq.com", "workday.com",
        "smartrecruiters.com", "icims.com", "taleo.net", "successfactors.com"
    ]
}

TIER_2 = {
    "points": 80,
    "domains": [
        "linkedin.com", "indeed.com", "rozee.pk", "mustakbil.com",
        "bayt.com", "naukrigulf.com"
    ]
}

TIER_3 = {
    "points": 60,
    "domains": [
        "glassdoor.com", "wellfound.com", "remoteok.com",
        "weworkremotely.com", "otta.com", "simplyhired.com"
    ]
}

EXCLUDED_KEYWORDS = ["ads", "sponsor", "promoted", "redirect", "track"]
INCLUSION_PATTERNS = ["/jobs/view", "/job/", "/careers/", "/apply"]

def get_tier_score(url: str) -> int:
    """Calculates the tier score of a URL."""
    domain = urllib.parse.urlparse(url).netloc.lower()
    for d in TIER_1["domains"]:
        if d in domain: return TIER_1["points"]
    for d in TIER_2["domains"]:
        if d in domain: return TIER_2["points"]
    for d in TIER_3["domains"]:
        if d in domain: return TIER_3["points"]
    return 30

def get_freshness_score(date_posted: Optional[str]) -> int:
    """Calculates freshness score. Returns -9999 for jobs > 30 days old."""
    if not date_posted:
        return 0

    try:
        dt = dateutil.parser.parse(date_posted)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        days_ago = (now - dt).days

        if days_ago <= 1: return 20
        if days_ago <= 7: return 10
        if days_ago <= 30: return 0
        return -9999
    except Exception:
        return 0

def filter_and_rank(tagged_urls: List[Dict], limit: int = 20) -> List[Dict]:
    """
    Filters and ranks tagged URLs based on tier and freshness.
    """
    results = []
    seen_company_keys = {}

    for item in tagged_urls:
        url = item["url"]
        url_lower = url.lower()

        # Freshness (Note: Stage 2 usually doesn't have date_posted yet unless it was in search results)
        # For now, we'll assume we don't have it here yet, but we'll apply it in Stage 5 after scraping.
        # However, the task says Stage 2 should do it. If we don't have date_posted, freshness_score is 0.
        freshness_score = get_freshness_score(item.get("date_posted"))

        if freshness_score == -9999:
            continue

        is_tier_1 = any(d in url_lower for d in TIER_1["domains"])
        has_pattern = any(pattern in url_lower for pattern in INCLUSION_PATTERNS)

        if not (is_tier_1 or has_pattern):
            continue

        if any(keyword in url_lower for keyword in EXCLUDED_KEYWORDS):
            continue

        tier_score = get_tier_score(url)
        score = tier_score + freshness_score

        domain = urllib.parse.urlparse(url).netloc.lower()
        company_key = domain
        if any(d in domain for d in ["greenhouse.io", "lever.co", "ashbyhq.com"]):
            path_parts = urllib.parse.urlparse(url).path.split('/')
            if len(path_parts) > 1:
                company_key = f"{domain}/{path_parts[1]}"

        if company_key not in seen_company_keys or score > seen_company_keys[company_key]["score"]:
            item["score"] = score
            seen_company_keys[company_key] = item

    sorted_results = sorted(seen_company_keys.values(), key=lambda x: x["score"], reverse=True)
    return sorted_results[:limit]
