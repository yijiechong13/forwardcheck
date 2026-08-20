"""Node 1 — normalise.

Forwarded messages arrive wrapped in noise: urgency banners, emoji, "forward to
everyone" appeals, and shorthand dates. Stripping that before decomposition
matters for two reasons: the noise is not checkable, and it pollutes lexical
retrieval with high-frequency junk tokens.

The removed markers are not simply discarded — they are recorded in the trace,
because "this message told you to forward it" is itself a useful signal.
"""

from __future__ import annotations

import re
import time

from app.pipeline.graph import PipelineState

# Appeals to forward, urgency banners, and source-laundering phrases.
#
# Order matters: the longest, most specific patterns run first, so a leading
# "Please " is consumed as part of "please forward ..." rather than being
# orphaned when a shorter pattern matches the tail first.
_FORWARD_MARKERS = [
    r"(?:please\s+|pls\s+|kindly\s+)?forward(?:ed)?\s+(?:this|it|these)?\s*(?:message|msg|to)?\s*(?:all|everyone|as many|your)?[^.!?]*",
    r"(?:please\s+|pls\s+|kindly\s+)?share\s+(?:this\s+)?(?:with|to)?\s*(?:all|everyone)[^.!?]*",
    r"\bbreaking\b\s*:?",
    r"\burgent\b\s*:?",
    r"\bimportant\b\s*:?",
    r"forwarded\s+many\s+times",
    r"received\s+from\s+(?:a\s+)?(?:reliable|trusted)\s+source[^.!?]*",
    r"my\s+(?:friend|cousin|uncle|aunt)\s+works?\s+(?:in|at)[^.!?]*",
]

_EMOJI = re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0000FE0F\U00002B00-\U00002BFF]+"
)

_MONTHS = {
    "jan": "01", "feb": "02", "mar": "03", "apr": "04", "may": "05", "jun": "06",
    "jul": "07", "aug": "08", "sep": "09", "sept": "09", "oct": "10",
    "nov": "11", "dec": "12",
}

# "1 Sept", "31 Aug 2026", "1st September"
_DATE = re.compile(
    r"\b(\d{1,2})(?:st|nd|rd|th)?\s+"
    r"(jan|feb|mar|apr|may|jun|jul|aug|sept|sep|oct|nov|dec)[a-z]*\.?"
    r"(?:\s+(\d{4}))?\b",
    re.IGNORECASE,
)


def normalise(state: PipelineState) -> PipelineState:
    started = time.perf_counter()
    original = state.raw_message
    text = original
    removed: list[str] = []

    emoji_found = _EMOJI.findall(text)
    if emoji_found:
        removed.extend(emoji_found)
        text = _EMOJI.sub(" ", text)

    for pattern in _FORWARD_MARKERS:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            fragment = match.group(0).strip()
            if fragment:
                removed.append(fragment)
        text = re.sub(pattern, " ", text, flags=re.IGNORECASE)

    dates_normalised: dict[str, str] = {}
    for match in _DATE.finditer(text):
        day, month, year = match.group(1), match.group(2).lower(), match.group(3)
        month_num = _MONTHS.get(month[:4]) or _MONTHS.get(month[:3])
        if month_num:
            # Year is often omitted in forwards; record it as unspecified rather
            # than guessing, so the freshness node does not trust a made-up year.
            iso = f"{year}-{month_num}-{int(day):02d}" if year else f"????-{month_num}-{int(day):02d}"
            dates_normalised[match.group(0).strip()] = iso

    # Collapse whitespace and tidy punctuation left behind by removals.
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+([.,!?;:])", r"\1", text)
    text = re.sub(r"([.!?])\s*\1+", r"\1", text)
    text = re.sub(r"^\s*[.,!?;:]+\s*", "", text)
    text = text.strip()

    state.normalised_message = text
    state.normalisation_notes = {
        "removed": removed[:10],
        "datesNormalised": dates_normalised,
        "charsBefore": len(original),
        "charsAfter": len(text),
        "hadForwardAppeal": any(
            re.search(p, original, re.IGNORECASE) for p in _FORWARD_MARKERS[:3]
        ),
    }

    state.add_step(
        node="normalise",
        summary=(
            f"Stripped {len(removed)} forwarding marker(s), normalised "
            f"{len(dates_normalised)} date reference(s)"
        ),
        duration_ms=int((time.perf_counter() - started) * 1000),
        details=state.normalisation_notes,
    )
    return state
