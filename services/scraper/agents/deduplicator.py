"""
Deduplication Module (v3)
Uses MinHash LSH to detect near-duplicate job descriptions.
Eliminates reposts and "refreshed ghosts" with >80% similarity.
"""

import re
from typing import List, Dict
from datasketch import MinHash, MinHashLSH

def preprocess(text: str) -> List[str]:
    """Basic shingling for MinHash."""
    text = re.sub(r'[^\w\s]', '', text.lower())
    tokens = text.split()
    # 3-word shingles
    return [" ".join(tokens[i:i+3]) for i in range(len(tokens)-2)]

def deduplicate_content(jobs: List[Dict], threshold: float = 0.8) -> List[Dict]:
    """Removes near-duplicate job listings based on JD text."""
    lsh = MinHashLSH(threshold=threshold, num_perm=128)
    unique_jobs = []

    for i, job in enumerate(jobs):
        jd = job.get("jd_text") or ""
        if len(jd) < 100: # Too short to deduplicate reliably
            unique_jobs.append(job)
            continue

        mh = MinHash(num_perm=128)
        for s in preprocess(jd):
            mh.update(s.encode('utf8'))

        # Check for near-duplicates
        result = lsh.query(mh)
        if not result:
            lsh.insert(f"job_{i}", mh)
            unique_jobs.append(job)
        else:
            print(f"Skipping near-duplicate: {job.get('title')} at {job.get('company')}")

    return unique_jobs
