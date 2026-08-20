"""Fetching (SSRF, limits), chunking, caching, and search normalisation."""

from __future__ import annotations

import time

import httpx
import pytest

from app.pipeline.chunk import chunk_blocks, snippet_chunk
from app.services.cache import TTLCache
from app.services.fetch import (
    FetchError,
    check_url_allowed,
    extract_readable,
    fetch_page,
)
from app.services.usage import UsageMeter


# ---------------------------------------------------------------------------
# SSRF protection
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("url", [
    "ftp://example.com/file",
    "file:///etc/passwd",
    "http://127.0.0.1/admin",
    "http://localhost:8000/internal",
    "http://192.168.1.10/router",
    "http://10.0.0.5/",
    "http://169.254.169.254/latest/meta-data/",  # cloud metadata endpoint
    "http://[::1]/",
    "http://0.0.0.0/",
])
def test_unsafe_urls_are_rejected(url):
    with pytest.raises(FetchError):
        check_url_allowed(url)


def test_redirect_to_private_address_is_rejected(monkeypatch, tmp_path):
    monkeypatch.setattr("app.config.settings.cache_dir", tmp_path)

    def handler(request):
        if request.url.path == "/start":
            return httpx.Response(302, headers={"location": "http://127.0.0.1/internal"})
        return httpx.Response(200, text="should never get here")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    monkeypatch.setattr("app.services.fetch._is_public_address",
                        lambda host: host != "127.0.0.1")
    with pytest.raises(FetchError) as excinfo:
        fetch_page("https://example.com/start", UsageMeter(), http_client=client)
    assert excinfo.value.kind == "address_not_public"


# ---------------------------------------------------------------------------
# Fetch limits and content handling
# ---------------------------------------------------------------------------

def _public(monkeypatch):
    monkeypatch.setattr("app.services.fetch._is_public_address", lambda host: True)


def test_non_html_content_type_is_rejected(monkeypatch, tmp_path):
    monkeypatch.setattr("app.config.settings.cache_dir", tmp_path)
    _public(monkeypatch)
    client = httpx.Client(transport=httpx.MockTransport(
        lambda r: httpx.Response(200, headers={"content-type": "application/pdf"}, content=b"%PDF")
    ))
    with pytest.raises(FetchError) as excinfo:
        fetch_page("https://example.com/doc.pdf", UsageMeter(), http_client=client)
    assert excinfo.value.kind == "content_type_not_text"


def test_oversized_response_is_truncated_not_crashed(monkeypatch, tmp_path):
    monkeypatch.setattr("app.config.settings.cache_dir", tmp_path)
    monkeypatch.setattr("app.config.settings.fetch_max_bytes", 2000)
    _public(monkeypatch)
    huge = "<html><body>" + "<p>Row of policy text here.</p>" * 500 + "</body></html>"
    client = httpx.Client(transport=httpx.MockTransport(
        lambda r: httpx.Response(200, headers={"content-type": "text/html"}, text=huge)
    ))
    page = fetch_page("https://example.com/big", UsageMeter(), http_client=client)
    assert sum(len(t) for _, t in page.blocks) <= 2100


def test_too_many_redirects_fails(monkeypatch, tmp_path):
    monkeypatch.setattr("app.config.settings.cache_dir", tmp_path)
    _public(monkeypatch)
    client = httpx.Client(transport=httpx.MockTransport(
        lambda r: httpx.Response(302, headers={"location": "https://example.com/loop"})
    ))
    with pytest.raises(FetchError) as excinfo:
        fetch_page("https://example.com/loop", UsageMeter(), http_client=client)
    assert excinfo.value.kind == "too_many_redirects"


def test_fetch_records_final_canonical_url_and_caches(monkeypatch, tmp_path):
    monkeypatch.setattr("app.config.settings.cache_dir", tmp_path)
    _public(monkeypatch)

    def handler(request):
        if request.url.path == "/old":
            return httpx.Response(301, headers={"location": "https://example.com/new"})
        return httpx.Response(200, headers={"content-type": "text/html"},
                              text="<html><body><p>Advisory text body of the page.</p></body></html>")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    meter = UsageMeter()
    page = fetch_page("https://example.com/old", meter, http_client=client)
    assert page.url == "https://example.com/new"
    assert meter.fetches == 1
    # Second call: served from cache, no new fetch charge.
    page2 = fetch_page("https://example.com/old", meter, http_client=client)
    assert page2.from_cache and meter.fetches == 1 and meter.cache_hits == 1


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------

def test_extraction_skips_boilerplate_and_keeps_headings():
    html = """<html><head><title>HSA | Recall</title></head><body>
      <nav><a href='/'>Home</a><a href='/about'>About</a></nav>
      <h2>Affected batch</h2><p>Batch 0575E exceeds cadmium limits.</p>
      <aside>Related links</aside><script>track()</script>
      <footer>Contact us</footer></body></html>"""
    title, blocks = extract_readable(html)
    text = " ".join(t for _, t in blocks)
    assert title.startswith("HSA")
    assert "Batch 0575E" in text
    assert ("heading", "Affected batch") in blocks
    assert "Home" not in text and "track()" not in text and "Contact us" not in text


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

def _blocks(n_paragraphs=6):
    blocks = [("heading", "Section A")]
    for i in range(n_paragraphs):
        blocks.append(("text", f"Paragraph {i} about the policy with date 1 May 2026 and amount $5,000. " * 4))
    return blocks


def test_chunks_respect_size_and_carry_metadata():
    chunks = chunk_blocks(
        _blocks(), url="https://x.gov.sg/a", title="T", publisher="x.gov.sg",
        tier="official", published_at="2026-05-01", query="q", max_chars=600, overlap=80,
    )
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk.text) <= 600 + 100  # cap plus one carried block
        assert chunk.url and chunk.publisher and chunk.tier == "official"
        assert chunk.retrieved_at and chunk.query == "q"
        assert chunk.from_full_page is True


def test_headings_bind_to_their_text():
    blocks = [("heading", "Penalties"), ("text", "Fine up to $5,000 on conviction."),
              ("heading", "Eligibility"), ("text", "Applies to pet cats only, not community cats.")]
    chunks = chunk_blocks(blocks, url="u", title="T", publisher="p", tier="official",
                          published_at=None, query="q")
    by_heading = {c.heading: c.text for c in chunks}
    assert "Fine up to $5,000" in by_heading["Penalties"]
    assert "community cats" in by_heading["Eligibility"]


def test_snippet_chunk_is_marked_weak():
    chunk = snippet_chunk(snippet="s", url="u", title="t", publisher="p",
                          tier="secondary", published_at=None, query="q")
    assert chunk.from_full_page is False


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

def test_cache_hits_and_expiry(tmp_path):
    cache = TTLCache("t", ttl_seconds=1, root=tmp_path)
    cache.set({"q": "x"}, [1, 2])
    assert cache.get({"q": "x"}) == [1, 2]
    assert cache.get({"q": "different"}) is None
    time.sleep(1.05)
    assert cache.get({"q": "x"}) is None


def test_cache_keys_are_parameter_sensitive(tmp_path):
    cache = TTLCache("t", ttl_seconds=60, root=tmp_path)
    cache.set({"provider": "tavily", "q": "a", "limit": 4}, "four")
    assert cache.get({"provider": "tavily", "q": "a", "limit": 5}) is None


# ---------------------------------------------------------------------------
# Mock mode makes zero network calls
# ---------------------------------------------------------------------------

def test_mock_mode_verification_opens_no_sockets(monkeypatch):
    import socket

    def explode(*args, **kwargs):
        raise AssertionError("network call attempted in mock mode")

    monkeypatch.setattr(socket.socket, "connect", explode)
    monkeypatch.setattr(socket, "getaddrinfo", explode)

    from app.pipeline.runner import run_verification
    response = run_verification(
        "From 1 Sept, HDB cat owners with more than 2 cats will be fined $5,000."
    )
    assert response.overall_verdict
