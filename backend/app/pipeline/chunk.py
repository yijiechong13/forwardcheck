"""Source-side document chunking.

Distinct from user-message claim decomposition: decomposition splits the
*forwarded message* into checkable assertions, while chunking splits a
*retrieved document* into gradeable passages. They answer different questions
and share no code.

Strategy: heading-aware, paragraph-preserving. Blocks accumulate under their
nearest heading until the size cap; a block is never split mid-way unless it
alone exceeds the cap, so dates, amounts and short table rows stay intact.
Overlap carries the tail of the previous chunk forward so a fact straddling a
boundary appears whole in at least one chunk.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.config import settings


@dataclass
class Chunk:
    chunk_id: str
    text: str
    heading: str
    # --- provenance metadata, attached to every chunk ---
    url: str
    title: str
    publisher: str
    tier: str
    published_at: str | None
    retrieved_at: str
    jurisdiction: str
    query: str
    #: False when only the search snippet was available (fetch failed).
    from_full_page: bool = True


def chunk_blocks(
    blocks: list[tuple[str, str]],
    *,
    url: str,
    title: str,
    publisher: str,
    tier: str,
    published_at: str | None,
    query: str,
    jurisdiction: str = "Singapore",
    max_chars: int | None = None,
    overlap: int | None = None,
) -> list[Chunk]:
    max_chars = max_chars or settings.chunk_max_chars
    overlap = overlap if overlap is not None else settings.chunk_overlap_chars
    retrieved_at = datetime.now(timezone.utc).isoformat()

    chunks: list[Chunk] = []
    heading = title or ""
    current: list[str] = []
    current_len = 0

    def flush() -> None:
        nonlocal current, current_len
        if not current:
            return
        text = "\n".join(current).strip()
        # Floor low enough that a short, dense advisory line ("Fine up to
        # $5,000 on conviction.") survives — those are often the whole point.
        if len(text) < 25:
            current, current_len = [], 0
            return
        chunks.append(
            Chunk(
                chunk_id=f"web-{len(chunks) + 1}",
                text=text,
                heading=heading,
                url=url,
                title=title,
                publisher=publisher,
                tier=tier,
                published_at=published_at,
                retrieved_at=retrieved_at,
                jurisdiction=jurisdiction,
                query=query,
            )
        )
        # Overlap: carry the tail forward so boundary-straddling facts
        # appear whole in the next chunk too.
        tail = text[-overlap:] if overlap else ""
        current = [tail] if tail else []
        current_len = len(tail)

    for kind, text in blocks:
        if kind == "heading":
            flush()
            heading = text
            continue
        if current_len + len(text) > max_chars and current:
            flush()
        # A single block larger than the cap is split on sentence-ish
        # boundaries as a last resort rather than dropped.
        while len(text) > max_chars:
            cut = text.rfind(". ", 0, max_chars)
            cut = cut + 1 if cut > max_chars // 2 else max_chars
            current.append(text[:cut])
            current_len += cut
            flush()
            text = text[cut:].strip()
        if text:
            current.append(text)
            current_len += len(text)

    flush()
    # Re-number after the fact so ids are stable and unique per document call.
    for index, chunk in enumerate(chunks, start=1):
        chunk.chunk_id = f"web-{index}"
    return chunks


def snippet_chunk(
    *, snippet: str, url: str, title: str, publisher: str, tier: str,
    published_at: str | None, query: str,
) -> Chunk:
    """Wrap a bare search snippet as weak evidence when the fetch failed."""
    return Chunk(
        chunk_id="snippet-1",
        text=snippet,
        heading=title,
        url=url,
        title=title,
        publisher=publisher,
        tier=tier,
        published_at=published_at,
        retrieved_at=datetime.now(timezone.utc).isoformat(),
        jurisdiction="Unknown",
        query=query,
        from_full_page=False,
    )
