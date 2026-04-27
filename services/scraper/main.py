"""
Nokri Scraper Service (v2-hardened)
FastAPI entry point with enhanced monitoring and strict validation.
"""

import os
import sys
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from services.scraper.agents import orchestrator
from services.scraper.agents.token_tracker import tracker
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI(
    title="Nokri Job Discovery Agent",
    version="2.1.0-hardened"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class DiscoverRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=100)
    location: str = Field(..., min_length=2, max_length=100)
    limit: int = Field(default=20, ge=1, le=50)
    max_age_days: int = Field(default=30, ge=1, le=90)
    structured_only: bool = False

@app.get("/health")
async def health():
    return {"status": "healthy", "version": "2.1.0-hardened"}

@app.get("/stats")
async def stats():
    return {
        "status": "healthy",
        "token_usage": tracker.report(),
        "orchestrator_metrics": orchestrator.ORCHESTRATOR_STATS,
        "config": {
            "structured_path": "JobSpy",
            "unstructured_path": "ScrapeGraphAI + Gemini 2.0 Flash"
        }
    }

@app.post("/discover")
async def discover(request: DiscoverRequest):
    """
    Hardened endpoint to discover jobs.
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
            "token_usage": tracker.report(),
            "metrics": {
                "request_id": os.getpid(), # Simple identifier
                "status": "success" if jobs else "no_results"
            }
        }
    except Exception as e:
        print(f"ERROR in /discover: {str(e)}", file=sys.stderr)
        raise HTTPException(status_code=500, detail="Internal processing error")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
