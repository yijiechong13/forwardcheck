"""Node 2 — decompose.

Forwarded messages bundle several assertions into one sentence, and a single
verdict on the whole message destroys that structure. "The deadline is real but
the fine is not" is only expressible if the message is split first.

Strategy (deterministic, no LLM):

  1. Split into sentences.
  2. Split each sentence on coordinating conjunctions that join independent
     assertions ("and", "but"), but only when both sides carry a verb — so
     "cats and dogs" stays whole while "X will be fined and Y will remove" splits.
  3. Drop fragments that are not checkable (appeals, opinions, questions).
  4. Rewrite each fragment into a standalone claim by carrying the subject
     forward, so a clause like "AVS will remove the extra cats" survives on its own.

The LLM adapter can replace this wholesale later; this is the measurable baseline.
"""

from __future__ import annotations

import re
import time

from app.pipeline.graph import PipelineState

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")

# Conjunctions that usually join two independent assertions in these messages.
#
# Two alternatives, because forwarded text joins clauses in two shapes:
#   (a) a fresh subject + auxiliary  -> "... and AVS will remove the cats"
#   (b) a shared subject, elided     -> "arrested at Changi and convicted under ..."
# Case (b) matters most here: "arrested and convicted" are two different rungs
# of the legal ladder and must get separate verdicts, so splitting on a bare
# status participle is deliberate rather than incidental.
_STATUS_PARTICIPLE = (
    r"charged|convicted|sentenced|arrested|jailed|fined|detained|released|"
    r"acquitted|investigated|banned|recalled|prosecuted|remanded"
)

_CLAUSE_SPLIT = re.compile(
    r"\s+(?:and|but|while|whereas)\s+(?="
    # (a) new subject followed by an auxiliary/verb
    r"(?:(?:the\s+|all\s+|any\s+|no\s+)?[A-Za-z][\w'’\-]*\s+"
    r"(?:will|is|are|was|were|has|have|had|must|may|can|could|would|should|"
    r"shall|does|do|did|faces?|remains?)"
    r"|"
    # (b) elided subject: conjunction directly before a status participle
    rf"(?:{_STATUS_PARTICIPLE})\b"
    r")"
    r")",
    re.IGNORECASE,
)

# Fragments with no verifiable content.
_NON_CHECKABLE = [
    r"^\s*(?:please|pls|kindly)\b",
    r"^\s*(?:thanks|thank you|tq)\b",
    r"\?\s*$",  # questions assert nothing
    r"^\s*(?:i think|in my opinion|imo|scary|so sad|omg|wow)\b",
    r"^\s*(?:stay safe|be careful|take care|god bless)\b",
    r"^\s*\W*$",  # punctuation-only residue
]

_MIN_CLAIM_CHARS = 12

# Appositive scope-expanders: "All cats, including community cats, must be
# licensed" asserts two separable things — the rule, and that the rule covers a
# specific extra group. Those routinely have *different* verdicts (the deadline
# is real; extending it to community cats is not), so they are split into two
# claims rather than graded as one.
_SCOPE_APPOSITIVE = re.compile(
    r"^(?P<head>.*?),\s*(?:including|even|also)\s+(?P<scope>[^,]+?),\s*(?P<tail>.+)$",
    re.IGNORECASE,
)


def _split_scope_appositive(sentence: str) -> list[str] | None:
    """Split "All X, including Y, must Z" into the rule and the scope claim."""
    match = _SCOPE_APPOSITIVE.match(sentence.strip())
    if not match:
        return None
    head, scope, tail = (
        match.group("head").strip(),
        match.group("scope").strip(),
        match.group("tail").strip(),
    )
    if not head or not scope or not tail:
        return None
    # The head keeps the rule; the appositive becomes its own scope claim.
    # "All cats" in the head is downgraded to "Cats", because the "all" was
    # doing the work of the appositive that has just been split off — leaving
    # it would make the head claim assert the very over-generalisation we
    # extracted, and both halves would then be graded as the same error.
    head = re.sub(r"^all\s+", "", head, flags=re.IGNORECASE)
    if head and head[0].islower():
        head = head[0].upper() + head[1:]
    return [f"{head} {tail}", f"{scope} {tail}"]


def _is_checkable(fragment: str) -> bool:
    if len(fragment.strip()) < _MIN_CLAIM_CHARS:
        return False
    if any(re.search(p, fragment, re.IGNORECASE) for p in _NON_CHECKABLE):
        return False
    # A claim needs a verb to assert anything.
    return bool(
        re.search(
            r"\b(?:is|are|was|were|will|has|have|had|must|may|can|been|being|"
            r"faces?|faced|remains?|becomes?|said|says|announced|issued|"
            r"charged|convicted|sentenced|arrested|investigated|banned|"
            r"recalled|fined|removed?|licensed|passed|takes?|took)\b",
            fragment,
            re.IGNORECASE,
        )
    )


def _leading_subject(clause: str) -> str:
    """Best-effort subject of the first clause, for carrying into elided ones.

    Handles "He was arrested ..." -> "He", and "Rocky's owner has been ..." ->
    "Rocky's owner". Returns "" when no confident subject is found, in which
    case the clause is left as-is rather than being given a wrong subject.
    """
    match = re.match(
        r"^\s*((?:[A-Z][\w'’\-]*|The|A|An)(?:\s+[\w'’\-]+){0,2}?)\s+"
        r"(?:was|were|is|are|has|have|had|will|must)\b",
        clause.strip(),
    )
    return match.group(1).strip() if match else ""


def _tidy(fragment: str) -> str:
    text = re.sub(r"\s+", " ", fragment).strip(" ,;:")
    text = re.sub(r"^(?:that|and|but|so|then|also)\s+", "", text, flags=re.IGNORECASE)
    if text and text[0].islower():
        text = text[0].upper() + text[1:]
    if text and text[-1] not in ".!?":
        text += "."
    return text


def decompose(state: PipelineState) -> PipelineState:
    started = time.perf_counter()
    message = state.normalised_message or state.raw_message

    fragments: list[tuple[str, str]] = []  # (claim_text, source_sentence)
    dropped: list[str] = []

    for sentence in _SENTENCE_SPLIT.split(message):
        sentence = sentence.strip()
        if not sentence:
            continue
        scope_split = _split_scope_appositive(sentence)
        if scope_split:
            for part in scope_split:
                if _is_checkable(part):
                    fragments.append((_tidy(part), sentence))
            continue

        parts = _CLAUSE_SPLIT.split(sentence)
        subject = _leading_subject(parts[0]) if len(parts) > 1 else ""
        for index, part in enumerate(parts):
            part = part.strip()
            if not part:
                continue
            # A clause split off an elided subject ("... and convicted under X")
            # is not a standalone claim until the subject is restored.
            if index > 0 and subject and re.match(
                rf"^(?:{_STATUS_PARTICIPLE})\b", part, re.IGNORECASE
            ):
                part = f"{subject} was {part}"
            if _is_checkable(part):
                fragments.append((_tidy(part), sentence))
            elif len(part) >= 4:
                dropped.append(part)

    # Store as plain tuples; the route node builds the Claim objects, since it
    # is the node that knows the status type and domain.
    state.claim_drafts = fragments

    state.add_step(
        node="decompose",
        summary=(
            f"Extracted {len(fragments)} atomic claim(s); "
            f"dropped {len(dropped)} non-checkable fragment(s)"
        ),
        duration_ms=int((time.perf_counter() - started) * 1000),
        details={
            "claims": [text for text, _ in fragments],
            "droppedNonCheckable": dropped[:6],
        },
    )
    return state
