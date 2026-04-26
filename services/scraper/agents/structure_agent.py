"""
Structure Agent Module (v2)
Normalizes job data using pruning, TOON compression, and instructor-led LLM extraction.
"""

import json
import os
import sys
import asyncio
from typing import List, Dict, Optional
from pydantic import BaseModel
import instructor
from litellm import completion
from bs4 import BeautifulSoup
import toon
from services.scraper.agents.token_tracker import tracker

# Define the schema for instructor
class JobSchema(BaseModel):
    title: str
    company: str
    location: str
    salary_min: float | None
    salary_max: float | None
    salary_currency: str | None
    job_type: str | None
    jd_text: str
    apply_url: str
    date_posted: str | None

def prune_html(raw_html: str) -> str:
    """Strips noise from HTML and returns clean text (max 2000 chars)."""
    if not raw_html:
        return ""
    try:
        soup = BeautifulSoup(raw_html, "html.parser")
        for tag in soup(["script", "style", "nav", "header", "footer", "aside", "iframe", "img", "svg"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        return text[:2000]
    except Exception as e:
        print(f"Error pruning HTML: {str(e)}", file=sys.stderr)
        return raw_html[:2000]

async def structure_single(item: Dict) -> Optional[Dict]:
    """Processes a single unstructured job using pruning, TOON, and instructor."""

    api_key = os.getenv("GEMINI_API_KEY")
    is_mock = not api_key or api_key == "your_gemini_api_key_here"

    if is_mock:
        print("WARNING: Running in mock mode - no GEMINI_API_KEY found", file=sys.stderr)
        return {
            **item,
            "company": item.get("company", "Mock Company (Mock Mode)"),
            "is_already_structured": True
        }

    # Improvement 1: DOM Pruning
    raw_text = item.get("jd_text", "")
    if "<" in raw_text and ">" in raw_text:
        pruned_text = prune_html(raw_text)
    else:
        pruned_text = raw_text[:2000]

    # Improvement 2: TOON Compression
    try:
        compressed_text = toon.encode(pruned_text)
    except Exception:
        compressed_text = pruned_text

    # Improvement 3: Flat JSON Input & Instructor
    client = instructor.from_litellm(completion)

    flat_json_input = {
        "task": "extract_job",
        "content": compressed_text,
        "extract": ["title", "company", "location", "salary_min", "salary_max",
                   "salary_currency", "job_type", "jd_text", "apply_url", "date_posted"]
    }

    try:
        loop = asyncio.get_event_loop()

        def call_llm():
            return client.chat.completions.create(
                model="gemini/gemini-2.0-flash",
                response_model=JobSchema,
                messages=[{
                    "role": "user",
                    "content": json.dumps(flat_json_input)
                }]
            )

        result = await loop.run_in_executor(None, call_llm)

        # Track tokens (Placeholder)
        tracker.log(1000)

        clean_job = result.model_dump()
        clean_job["source_score"] = item.get("source_score", 100)
        clean_job["source"] = item.get("source", "unknown")

        return clean_job
    except Exception as e:
        print(f"Error in Instructor LLM extraction: {str(e)}", file=sys.stderr)
        return item

async def structure(results: List[Dict]) -> List[Dict]:
    """
    Orchestrates structuring.
    Skips Path A jobs (already structured).
    """
    to_structure = [r for r in results if not r.get("is_already_structured")]
    already_structured = [r for r in results if r.get("is_already_structured")]

    structured_results = []
    batch_size = 10
    for i in range(0, len(to_structure), batch_size):
        batch = to_structure[i:i + batch_size]
        tasks = [structure_single(item) for item in batch]
        batch_results = await asyncio.gather(*tasks)
        structured_results.extend([r for r in batch_results if r])

    return already_structured + structured_results
