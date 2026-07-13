import time
from collections import defaultdict, deque


class SlidingWindowRateLimiter:
    """Small in-process limiter keyed by an operation bucket and caller key."""

    def __init__(self):
        self._attempts = defaultdict(deque)

    def allow(self, key: str, bucket: str, limit: int, window_seconds: int = 300) -> bool:
        now = time.monotonic()
        attempts = self._attempts[(bucket, key)]
        cutoff = now - window_seconds
        while attempts and attempts[0] <= cutoff:
            attempts.popleft()
        if len(attempts) >= limit:
            return False
        attempts.append(now)
        return True


rate_limiter = SlidingWindowRateLimiter()
