import time
from collections import defaultdict, deque
from threading import Lock


MAX_TRACKED_KEYS = 10000
SWEEP_INTERVAL_SECONDS = 5.0


class SlidingWindowRateLimiter:
    """Small in-process limiter keyed by an operation bucket and caller key."""

    def __init__(self):
        self._attempts = defaultdict(deque)
        self._lock = Lock()
        self._last_sweep_at = None

    def allow(self, key: str, bucket: str, limit: int, window_seconds: int = 300) -> bool:
        now = time.monotonic()
        composite_key = (bucket, key)
        with self._lock:
            attempts = self._attempts.get(composite_key)
            if attempts:
                self._remove_expired_attempts(attempts, now - window_seconds)
                if not attempts:
                    del self._attempts[composite_key]
            if self._last_sweep_at is None or now - self._last_sweep_at >= SWEEP_INTERVAL_SECONDS:
                self._remove_expired(now, window_seconds)
                self._last_sweep_at = now
            if composite_key not in self._attempts:
                self._make_room()
            attempts = self._attempts[composite_key]
            if len(attempts) >= limit:
                return False
            attempts.append(now)
            return True

    def _remove_expired(self, now: float, window_seconds: int) -> None:
        cutoff = now - window_seconds
        for composite_key, attempts in list(self._attempts.items()):
            self._remove_expired_attempts(attempts, cutoff)
            if not attempts:
                del self._attempts[composite_key]

    @staticmethod
    def _remove_expired_attempts(attempts, cutoff: float) -> None:
        while attempts and attempts[0] <= cutoff:
            attempts.popleft()

    def _make_room(self) -> None:
        while len(self._attempts) >= MAX_TRACKED_KEYS:
            oldest_key = min(self._attempts, key=lambda item: self._attempts[item][0])
            del self._attempts[oldest_key]


rate_limiter = SlidingWindowRateLimiter()
