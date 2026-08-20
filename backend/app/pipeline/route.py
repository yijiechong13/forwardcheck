"""Node 3 — route.

Assigns each draft claim a status type, domain, and jurisdiction. This is the
node that decides *what kind of question* is being asked, and it matters more
than it looks: routing determines which rung of which ladder the claim sits on,
which is what makes escalation detectable downstream.

Ordering is significant. Patterns are checked most-specific first, because
"will be fined $5,000" is a penalty claim, not merely a policy-in-effect claim,
and "automatically be jailed" is a sentence claim, not an arrest claim.
"""

from __future__ import annotations

import re
import time

from app.models.schemas import Claim, Verdict
from app.models.status import Domain, Jurisdiction, STATUS_DOMAIN, StatusType
from app.pipeline.graph import PipelineState

# (pattern, status) — evaluated in order, first match wins.
_STATUS_PATTERNS: list[tuple[str, StatusType]] = [
    # --- Legal ladder (most final first) ---
    (r"\bsentenc(?:ed|ing)\b|\bjail(?:ed)?\s+for\b|\byears?\s+(?:in\s+)?jail\b"
     r"|\bautomatically\s+(?:be\s+)?jailed\b|\bimprisoned\s+for\b", StatusType.SENTENCE),
    (r"\bconvict(?:ed|ion)\b|\bfound\s+guilty\b|\bpleaded\s+guilty\b", StatusType.CONVICTION),
    (r"\bcharg(?:ed|es)\b|\bfacing\s+court\b|\bcourt\s+action\b|\bprosecut(?:ed|ion)\b"
     r"|\bhauled\s+to\s+court\b", StatusType.CHARGE),
    (r"\barrest(?:ed)?\b|\bdetained\b|\bnabbed\b|\bapprehended\b", StatusType.ARREST),
    (r"\binvestigat(?:ed|ing|ion)\b|\bunder\s+probe\b|\bprobing\b|\blooking\s+into\b",
     StatusType.INVESTIGATION),
    (r"\breleased\b|\bacquitted\b|\bcleared\s+of\b|\bcase\s+dropped\b", StatusType.RELEASE),
    (r"\bbail(?:ed)?\b|\bout\s+on\s+bail\b|\bremanded\b", StatusType.BAIL),
    (r"\balleg(?:ed|ation|edly)\b|\brumou?r(?:ed)?\b|\bclaim(?:ed)?\s+that\b"
     r"|\bsuspected\s+of\b", StatusType.ALLEGATION),

    # --- Product safety ladder ---
    (r"\bban(?:ned|s)?\b|\bprohibit(?:ed|ion)\b|\bwithdrawn\s+from\s+sale\b", StatusType.BAN),
    (r"\brecall(?:ed|s)?\b.{0,40}\b(?:singapore|malaysia|local(?:ly)?|here)\b"
     r"|\b(?:singapore|malaysia|local)\b.{0,30}\brecall(?:ed|s)?\b", StatusType.LOCAL_RECALL),
    (r"\brecall(?:ed|s)?\b.{0,40}\b(?:overseas|abroad|us|uk|australia|japan|europe)\b"
     r"|\boverseas\s+recall\b", StatusType.OVERSEAS_RECALL),
    (r"\brecall(?:ed|s|ing)?\b", StatusType.LOCAL_RECALL),
    (r"\bwarning\b|\bwarned\b|\bdo\s+not\s+(?:eat|use|consume|buy)\b", StatusType.WARNING),
    (r"\badvisory\b|\badvis(?:ed|es)\b|\bcaution(?:ed)?\b", StatusType.ADVISORY),

    # --- Policy ladder ---
    (r"\bfine[ds]?\b|\bfined\s+\$|\bpenalt(?:y|ies)\b|\bcompound(?:ed)?\b"
     r"|\bwill\s+be\s+fined\b|\bmust\s+pay\b", StatusType.PENALTY),
    (r"\benforce(?:d|ment|ing)\b|\bwill\s+(?:be\s+)?(?:remove|confiscate|seize)"
     r"|\bcrackdown\b|\braids?\b", StatusType.ENFORCED),
    (r"\bby\s+\d{1,2}\s+\w+\b|\bdeadline\b|\bbefore\s+\d{1,2}\s+\w+\b"
     r"|\blast\s+day\b|\bmust\s+.{0,30}\bby\b", StatusType.DEADLINE),
    (r"\bfrom\s+\d{1,2}\s+\w+\b|\btakes?\s+effect\b|\bin\s+force\b|\beffective\b"
     r"|\bstarting\s+\w+\b|\bwith\s+effect\s+from\b", StatusType.EFFECTIVE),
    (r"\bpassed\b|\bapproved\b|\bgazetted\b|\benacted\b|\bannounced\b", StatusType.PASSED),
    (r"\bproposed?\b|\bconsultation\b|\bplan(?:s|ning)?\s+to\b|\bmay\s+introduce\b"
     r"|\bconsidering\b", StatusType.PROPOSED),

    # Requirement without an explicit date still asserts a rule is in effect.
    (r"\bmust\s+be\b|\brequired\s+to\b|\bmandatory\b|\bcompulsory\b", StatusType.EFFECTIVE),
]

_JURISDICTION_PATTERNS: list[tuple[str, Jurisdiction]] = [
    (r"\bsingapore\b|\bhdb\b|\bavs\b|\bnparks\b|\bspf\b|\bchangi\b|\bs\$|\bsgd\b"
     r"|\bmoh\b|\bhsa\b|\bsfa\b|\bica\b|\bmindef\b|\bns\b|\benlistment\b", Jurisdiction.SINGAPORE),
    (r"\bmalaysia\b|\bkuala lumpur\b|\bpdrm\b|\bkpdn\b|\bringgit\b|\brm\d|\bjohor\b"
     r"|\bpenang\b|\bselangor\b", Jurisdiction.MALAYSIA),
    (r"\b(?:the\s+)?(?:us|usa|uk|australia|japan|china|europe|america)\b"
     r"|\boverseas\b|\babroad\b", Jurisdiction.OVERSEAS),
]

#: Generalisation markers. "All X will automatically be Y" is a different kind
#: of claim from a specific event report, and it is almost always the escalated
#: part of a forward, so it is flagged for the grader.
_UNIVERSAL_MARKERS = re.compile(
    r"\ball\b|\bevery\b|\banyone\b|\bautomatic(?:ally)?\b|\balways\b|\bany\s+one\b"
    r"|\bthis\s+means\b|\bwill\s+be\s+jailed\b",
    re.IGNORECASE,
)


def _classify_status(text: str) -> StatusType:
    for pattern, status in _STATUS_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return status
    return StatusType.UNKNOWN


def _classify_jurisdiction(text: str, fallback: Jurisdiction) -> Jurisdiction:
    for pattern, jurisdiction in _JURISDICTION_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return jurisdiction
    return fallback


def route(state: PipelineState) -> PipelineState:
    started = time.perf_counter()
    whole_message = state.normalised_message or state.raw_message

    # Jurisdiction is usually stated once for the whole message, so resolve it
    # globally first and let individual claims override it.
    message_jurisdiction = _classify_jurisdiction(whole_message, Jurisdiction.UNKNOWN)

    claims: list[Claim] = []
    routing: dict[str, str] = {}

    for index, (text, source_span) in enumerate(state.claim_drafts, start=1):
        status = _classify_status(text)
        domain = STATUS_DOMAIN.get(status, Domain.UNKNOWN)
        jurisdiction = _classify_jurisdiction(text, message_jurisdiction)
        claim_id = f"c{index}"

        claim = Claim(
            id=claim_id,
            text=text,
            source_span=source_span,
            status_type=status,
            domain=domain,
            jurisdiction=jurisdiction,
            # Placeholder verdict; the verdict node decides. Defaulting to
            # abstention means a claim that somehow skips grading fails safe.
            verdict=Verdict.INSUFFICIENT,
            confidence=0.0,
            key_reason="",
        )
        # Not part of the API contract, used by grade/verdict.
        object.__setattr__(
            claim, "_is_universal", bool(_UNIVERSAL_MARKERS.search(text))
        )
        claims.append(claim)
        routing[claim_id] = f"{status.value}/{domain.value}/{jurisdiction.value}"

    state.claims = claims

    unknown = sum(1 for c in claims if c.status_type == StatusType.UNKNOWN.value)
    state.add_step(
        node="route",
        summary=(
            f"Routed {len(claims)} claim(s); {len(claims) - unknown} classified, "
            f"{unknown} unclassified"
        ),
        duration_ms=int((time.perf_counter() - started) * 1000),
        details={
            "routing": routing,
            "messageJurisdiction": message_jurisdiction.value,
            "universalClaims": [
                c.id for c in claims if getattr(c, "_is_universal", False)
            ],
        },
    )
    return state
