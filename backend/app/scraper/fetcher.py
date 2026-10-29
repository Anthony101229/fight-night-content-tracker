"""Polite HTTP fetching: a descriptive User-Agent, rate limiting, and an on-disk HTML cache."""

import hashlib
import re
import time
from pathlib import Path

import httpx

MAX_RETRIES = 3


class Fetcher:
    """Downloads pages one at a time, waiting between requests and caching the raw HTML.

    If a page was downloaded less than `cache_hours` ago it is read from disk instead,
    so re-running the scraper is fast and doesn't hit the website again.
    """

    def __init__(
        self,
        cache_dir: Path,
        delay_seconds: float,
        cache_hours: float,
        user_agent: str,
        transport: httpx.BaseTransport | None = None,  # tests pass a fake network here
    ) -> None:
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.delay_seconds = delay_seconds
        self.cache_seconds = cache_hours * 3600
        self.client = httpx.Client(
            headers={"User-Agent": user_agent},
            timeout=30,
            follow_redirects=True,
            transport=transport,
        )
        self._last_request_at = 0.0
        self.requests_made = 0
        self.cache_hits = 0

    def get(self, url: str) -> str:
        """Return the HTML for `url`, from the cache if fresh, otherwise from the network."""
        path = self._cache_path(url)
        if path.exists() and time.time() - path.stat().st_mtime < self.cache_seconds:
            self.cache_hits += 1
            return path.read_text(encoding="utf-8")

        for _attempt in range(MAX_RETRIES + 1):
            self._wait_for_rate_limit()
            response = self.client.get(url)
            self.requests_made += 1
            if response.status_code != 429:
                break
            # "Too Many Requests": wait as long as the server asks before trying again.
            time.sleep(float(response.headers.get("Retry-After", 30)))
        response.raise_for_status()
        path.write_text(response.text, encoding="utf-8")
        return response.text

    def close(self) -> None:
        """Close the underlying HTTP connection pool."""
        self.client.close()

    def _wait_for_rate_limit(self) -> None:
        wait = self._last_request_at + self.delay_seconds - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        self._last_request_at = time.monotonic()

    def _cache_path(self, url: str) -> Path:
        # Readable name from the page title, plus a short hash so two URLs never share a file.
        slug = re.sub(r"[^A-Za-z0-9]+", "_", url.rsplit("/", 1)[-1])[:80]
        digest = hashlib.sha256(url.encode()).hexdigest()[:8]
        return self.cache_dir / f"{slug}-{digest}.html"
