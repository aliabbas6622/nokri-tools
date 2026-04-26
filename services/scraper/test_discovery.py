import httpx
import asyncio
import sys
import json

async def test():
    print("Starting automated discovery test (v2)...")
    async with httpx.AsyncClient() as client:
        try:
            # Test /stats endpoint
            print("Checking /stats endpoint...")
            stats_resp = await client.get("http://localhost:8000/stats")
            assert stats_resp.status_code == 200
            print(f"Stats: {json.dumps(stats_resp.json(), indent=2)}")

            # Test /discover endpoint
            print("\nChecking /discover endpoint...")
            response = await client.post(
                "http://localhost:8000/discover",
                json={
                    "query": "software engineer",
                    "location": "Karachi Pakistan",
                    "limit": 5
                },
                timeout=180.0 # Increased timeout for ScrapeGraphAI
            )

            if response.status_code != 200:
                print(f"FAILED: Status code {response.status_code}")
                print(response.text)
                sys.exit(1)

            data = response.json()
            assert "jobs" in data
            assert isinstance(data["jobs"], list)
            assert "token_usage" in data

            print(f"SUCCESS: {data['count']} jobs found")
            print(f"Token Usage: {json.dumps(data['token_usage'], indent=2)}")
            for job in data["jobs"]:
                print(f"  - {job.get('title')} at {job.get('company')} (Score: {job.get('source_score')})")

        except Exception as e:
            print(f"FAILED: An error occurred: {str(e)}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

if __name__ == "__main__":
    asyncio.run(test())
