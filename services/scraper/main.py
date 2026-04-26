"""
Nokri Scraper Service (v2)
FastAPI entry point for the job discovery agent with token tracking and stats.
"""

import os
import sys
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from services.scraper.agents import orchestrator
from services.scraper.agents.token_tracker import tracker
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI(title="Nokri Job Discovery Agent")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class DiscoverRequest(BaseModel):
    query: str
    location: str
    limit: int = 20
    max_age_days: int = 30
    structured_only: bool = False

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.get("/stats")
async def stats():
    return {
        "status": "healthy",
        "token_tracker": tracker.report(),
        "paths": {
            "structured": "JobSpy (no LLM)",
            "unstructured": "ScrapeGraphAI + Toonify + Gemini"
        }
    }

@app.post("/discover")
async def discover(request: DiscoverRequest):
    """
    Endpoint to discover jobs based on query and location.
    """
    try:
        jobs = await orchestrator.discover_jobs(
            query=request.query,
            location=request.location,
            limit=request.limit
        )
        return {
            "jobs": jobs,
            "count": len(jobs),
            "token_usage": tracker.report()
        }
    except Exception as e:
        print(f"Error in discovery endpoint: {str(e)}", file=sys.stderr)
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
