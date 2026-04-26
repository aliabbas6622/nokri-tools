"""
Token Tracker Module
Monitors LLM token usage and call counts.
"""

class TokenTracker:
    def __init__(self):
        self.total_tokens = 0
        self.calls = 0

    def log(self, tokens_used: int):
        """Logs tokens used in an LLM call."""
        self.total_tokens += tokens_used
        self.calls += 1

    def report(self) -> dict:
        """Returns a report of token usage."""
        return {
            "total_tokens": self.total_tokens,
            "llm_calls": self.calls,
            "avg_tokens_per_call": (
                self.total_tokens / self.calls
                if self.calls > 0 else 0
            )
        }

# Global tracker instance
tracker = TokenTracker()
