"""Tests for the fetcher's cache and retry behaviour, using a fake network."""

from pathlib import Path

import httpx
import pytest

from app.scraper.fetcher import Fetcher

URL = "https://en.wikipedia.org/wiki/UFC_999"


def make_fetcher(tmp_path: Path, responses: list[httpx.Response], cache_hours: float = 24):
    """A Fetcher whose network replies with `responses` in order. Also returns the call log."""
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return responses[len(calls) - 1]

    fetcher = Fetcher(
        cache_dir=tmp_path,
        delay_seconds=0,
        cache_hours=cache_hours,
        user_agent="TestBot/1.0 (test@example.com)",
        transport=httpx.MockTransport(handler),
    )
    return fetcher, calls


def test_second_get_is_served_from_cache(tmp_path: Path) -> None:
    fetcher, calls = make_fetcher(tmp_path, [httpx.Response(200, text="<html>page</html>")])

    assert fetcher.get(URL) == "<html>page</html>"
    assert fetcher.get(URL) == "<html>page</html>"

    assert len(calls) == 1
    assert (fetcher.requests_made, fetcher.cache_hits) == (1, 1)
    assert calls[0].headers["User-Agent"] == "TestBot/1.0 (test@example.com)"


def test_expired_cache_is_refetched(tmp_path: Path) -> None:
    fetcher, calls = make_fetcher(
        tmp_path, [httpx.Response(200, text="old"), httpx.Response(200, text="new")], cache_hours=0
    )

    fetcher.get(URL)

    assert fetcher.get(URL) == "new"
    assert len(calls) == 2


def test_retries_after_429(tmp_path: Path) -> None:
    fetcher, calls = make_fetcher(
        tmp_path,
        [httpx.Response(429, headers={"Retry-After": "0"}), httpx.Response(200, text="ok")],
    )

    assert fetcher.get(URL) == "ok"
    assert len(calls) == 2


def test_errors_raise_and_are_not_cached(tmp_path: Path) -> None:
    fetcher, _ = make_fetcher(tmp_path, [httpx.Response(404)])

    with pytest.raises(httpx.HTTPStatusError):
        fetcher.get(URL)

    assert list(tmp_path.iterdir()) == []
