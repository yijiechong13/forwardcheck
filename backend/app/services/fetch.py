"""Safe webpage retrieval and main-content extraction.

Search snippets are usually too short to verify a status claim against, so
top-ranked results are fetched and their readable text extracted. Because the
URL being fetched originates from an external search provider, fetching is
treated as handling untrusted input:

  * http/https only;
  * the resolved IP is checked against private / loopback / link-local ranges
    before any request is sent (SSRF guard), and redirects are re-checked;
  * response size, timeout, redirect count and content-type are all capped;
  * no login walls or paywalls are bypassed — a 401/403/paywall page simply
    fails the fetch and the search snippet remains as weak evidence.

Extraction is a deliberately simple, dependency-free HTML-to-text pass built
on the stdlib parser: boilerplate containers (nav/header/footer/aside/script)
are skipped, headings are preserved as markers so the chunker can respect
section boundaries. It is *not* a readability engine and is documented as
such — .gov.sg advisory pages are structurally simple, which is what makes
this adequate for the MVP.
"""

from __future__ import annotations

import ipaddress
import logging
import socket
from dataclasses import dataclass, field
from html.parser import HTMLParser
from urllib.parse import urlparse

from app.config import settings

logger = logging.getLogger("forwardcheck.fetch")


class FetchError(Exception):
    def __init__(self, kind: str) -> None:
        self.kind = kind
        super().__init__(f"fetch error: {kind}")


# ---------------------------------------------------------------------------
# SSRF guard
# ---------------------------------------------------------------------------

def _is_public_address(host: str) -> bool:
    """True only when every resolved address is publicly routable."""
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return False
    addresses = {info[4][0] for info in infos}
    if not addresses:
        return False
    for raw in addresses:
        try:
            ip = ipaddress.ip_address(raw)
        except ValueError:
            return False
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            return False
    return True


def check_url_allowed(url: str) -> None:
    """Raise FetchError unless the URL is safe to fetch."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise FetchError("scheme_not_allowed")
    if not parsed.hostname:
        raise FetchError("no_host")
    # Reject literal IPs and hostnames resolving to non-public space alike.
    if not _is_public_address(parsed.hostname):
        raise FetchError("address_not_public")


# ---------------------------------------------------------------------------
# HTML -> readable text with heading markers
# ---------------------------------------------------------------------------

_SKIP_CONTAINERS = {"script", "style", "nav", "header", "footer", "aside", "noscript", "form", "svg"}
_BLOCK_TAGS = {"p", "li", "td", "th", "blockquote", "figcaption", "pre", "dd", "dt"}
_HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self._heading: str | None = None
        self._buffer: list[str] = []
        self.blocks: list[tuple[str, str]] = []  # (kind, text) kind: heading|text
        self.title = ""
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        if tag in _SKIP_CONTAINERS:
            self._skip_depth += 1
        elif tag == "title":
            self._in_title = True
        elif self._skip_depth == 0 and tag in _HEADING_TAGS:
            self._flush("text")
            self._heading = tag
        elif self._skip_depth == 0 and tag in _BLOCK_TAGS:
            self._flush("text")

    def handle_endtag(self, tag):
        if tag in _SKIP_CONTAINERS and self._skip_depth > 0:
            self._skip_depth -= 1
        elif tag == "title":
            self._in_title = False
        elif tag in _HEADING_TAGS and self._heading:
            self._flush("heading")
            self._heading = None
        elif tag in _BLOCK_TAGS:
            self._flush("text")

    def handle_data(self, data):
        if self._in_title:
            self.title += data
            return
        if self._skip_depth == 0 and data.strip():
            self._buffer.append(data.strip())

    def _flush(self, kind: str) -> None:
        if self._buffer:
            text = " ".join(self._buffer).strip()
            if len(text) > 2:
                self.blocks.append((kind if self._heading is None or kind == "heading" else "text", text))
            self._buffer = []

    def close(self):
        self._flush("text")
        super().close()


def extract_readable(html: str) -> tuple[str, list[tuple[str, str]]]:
    """Return (page_title, [(kind, text)]) where kind is heading|text."""
    parser = _TextExtractor()
    try:
        parser.feed(html)
        parser.close()
    except Exception:
        # A malformed page yields whatever was parsed before the failure.
        pass
    return parser.title.strip(), parser.blocks


# ---------------------------------------------------------------------------
# Fetching
# ---------------------------------------------------------------------------

@dataclass
class FetchedPage:
    url: str            # final canonical URL after redirects
    title: str
    blocks: list[tuple[str, str]] = field(default_factory=list)
    from_cache: bool = False


def fetch_page(url: str, meter, http_client=None) -> FetchedPage:
    """Fetch and extract one page, with cache, budgets and SSRF checks."""
    import httpx

    from app.services.cache import page_cache

    cache = page_cache()
    cached = cache.get({"url": url})
    if cached is not None:
        meter.record_cache_hit()
        return FetchedPage(
            url=cached["finalUrl"],
            title=cached["title"],
            blocks=[tuple(b) for b in cached["blocks"]],
            from_cache=True,
        )

    check_url_allowed(url)
    meter.charge_fetch()

    client = http_client or httpx.Client(
        timeout=settings.fetch_timeout_seconds,
        follow_redirects=False,
        headers={"User-Agent": "ForwardCheck/0.4 (verification tool; contact via repo)"},
    )

    current = url
    for _ in range(settings.fetch_max_redirects + 1):
        try:
            response = client.get(current)
        except httpx.TimeoutException as exc:
            raise FetchError("timeout") from exc
        except httpx.HTTPError as exc:
            raise FetchError("connection") from exc

        if response.status_code in (301, 302, 303, 307, 308):
            location = response.headers.get("location")
            if not location:
                raise FetchError("bad_redirect")
            current = str(httpx.URL(current).join(location))
            check_url_allowed(current)  # re-validate: redirects can pivot to internal hosts
            continue
        break
    else:
        raise FetchError("too_many_redirects")

    if response.status_code != 200:
        raise FetchError(f"status_{response.status_code}")

    content_type = response.headers.get("content-type", "").lower()
    if "html" not in content_type and "text/plain" not in content_type:
        raise FetchError("content_type_not_text")

    body = response.content[: settings.fetch_max_bytes]
    title, blocks = extract_readable(body.decode(response.encoding or "utf-8", errors="replace"))

    if not blocks:
        raise FetchError("no_extractable_text")

    cache.set(
        {"url": url},
        {"finalUrl": current, "title": title, "blocks": [list(b) for b in blocks]},
    )
    return FetchedPage(url=current, title=title, blocks=blocks)
