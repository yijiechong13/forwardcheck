"""Seeded evidence corpus.

EVERY DOCUMENT HERE IS HAND-WRITTEN SAMPLE DATA. Titles, snippets, and dates
resemble real advisories so the pipeline has something realistic to reason over,
but nothing was scraped and every URL is a labelled placeholder. `is_mock=True`
is set on all of them and surfaced in the UI.

Design note — the *absences* are the point. Two of the three clusters
deliberately stop one rung short of what the forwarded message claims:

  * ns-enlistment: arrest and charge exist; conviction and sentence do not.
  * rocky-case:    investigation and a statement exist; no charge does.

A retrieval corpus that can answer everything cannot demonstrate abstention,
and abstention is the behaviour this product is built around.
"""

from __future__ import annotations

from app.models.schemas import Evidence, SourceTier
from app.models.status import Jurisdiction, StatusType


def _doc(
    id: str,
    title: str,
    publisher: str,
    tier: SourceTier,
    jurisdiction: Jurisdiction,
    published_at: str,
    snippet: str,
    status_asserted: StatusType,
    topic: str,
    url_slug: str,
) -> Evidence:
    doc = Evidence(
        id=id,
        title=title,
        publisher=publisher,
        tier=tier,
        jurisdiction=jurisdiction,
        published_at=published_at,
        url=f"https://[sample-placeholder]/{url_slug}",
        snippet=snippet,
        status_asserted=status_asserted,
        is_mock=True,
    )
    # `topic` groups documents into clusters for retrieval diagnostics. It is
    # not part of the API contract, so it is attached rather than declared.
    object.__setattr__(doc, "_topic", topic)
    return doc


# ---------------------------------------------------------------------------
# Cluster 1 — HDB cat licensing (policy / Singapore)
# ---------------------------------------------------------------------------

CAT_LICENSING: list[Evidence] = [
    _doc(
        id="sg-avs-001",
        title="Cat Licensing Scheme: registration opens for pet cat owners",
        publisher="Animal & Veterinary Service (AVS), NParks",
        tier=SourceTier.OFFICIAL,
        jurisdiction=Jurisdiction.SINGAPORE,
        published_at="2026-06-02",
        snippet=(
            "Pet cat owners are required to license their cats under the Cat "
            "Licensing Scheme. Licences may be obtained online at no cost during "
            "the initial registration period, which closes on 31 August. Owners "
            "who license their cats within this window will not be charged a fee."
        ),
        status_asserted=StatusType.DEADLINE,
        topic="cat-licensing",
        url_slug="avs/cat-licensing-scheme",
    ),
    _doc(
        id="sg-mnd-002",
        title="Cat management framework announced following public consultation",
        publisher="Ministry of National Development",
        tier=SourceTier.OFFICIAL,
        jurisdiction=Jurisdiction.SINGAPORE,
        published_at="2026-05-20",
        snippet=(
            "The new cat management framework introduces licensing for pet cats "
            "and lifts the previous prohibition on keeping cats in HDB flats. "
            "HDB households may keep up to two licensed cats. The framework takes "
            "effect following a transition period for existing owners."
        ),
        status_asserted=StatusType.PASSED,
        topic="cat-licensing",
        url_slug="mnd/cat-management-framework",
    ),
    _doc(
        id="sg-sso-003",
        title="Animals and Birds Act — penalties for licensing offences",
        publisher="Singapore Statutes Online",
        tier=SourceTier.PRIMARY,
        jurisdiction=Jurisdiction.SINGAPORE,
        published_at="2026-01-15",
        snippet=(
            "A person who contravenes the licensing requirement shall be guilty of "
            "an offence and shall be liable on conviction to a fine not exceeding "
            "$5,000. The amount stated is a maximum penalty which the court may "
            "impose on conviction; it is not a fixed or automatic fine."
        ),
        status_asserted=StatusType.PENALTY,
        topic="cat-licensing",
        url_slug="sso/animals-and-birds-act-s45",
    ),
    _doc(
        id="sg-avs-004",
        title="FAQ: households that already have more than two cats",
        publisher="Animal & Veterinary Service (AVS), NParks",
        tier=SourceTier.OFFICIAL,
        jurisdiction=Jurisdiction.SINGAPORE,
        published_at="2026-06-02",
        snippet=(
            "Existing owners who have more cats than the cap when the scheme "
            "begins may continue to keep all of their cats, provided every cat is "
            "licensed. Owners will not be required to give up or rehome their "
            "cats. AVS will not remove cats from households that comply with "
            "licensing requirements. The focus is on education and voluntary "
            "compliance rather than enforcement action."
        ),
        status_asserted=StatusType.EFFECTIVE,
        topic="cat-licensing",
        url_slug="avs/cat-licensing-faq-existing-owners",
    ),
    _doc(
        id="sg-avs-005",
        title="Community cats and the licensing scheme",
        publisher="Animal & Veterinary Service (AVS), NParks",
        tier=SourceTier.OFFICIAL,
        jurisdiction=Jurisdiction.SINGAPORE,
        published_at="2026-06-10",
        snippet=(
            "Licensing applies to owned pet cats. Community cats, which do not "
            "have an owner, are not required to be licensed. Community cats "
            "continue to be managed under a separate sterilisation and care "
            "programme run with animal welfare groups."
        ),
        status_asserted=StatusType.EFFECTIVE,
        topic="cat-licensing",
        url_slug="avs/community-cats",
    ),
    _doc(
        id="sg-news-006",
        title="Cat owners have until end-August to license their pets",
        publisher="Channel NewsAsia",
        tier=SourceTier.CREDIBLE_NEWS,
        jurisdiction=Jurisdiction.SINGAPORE,
        published_at="2026-06-03",
        snippet=(
            "Pet cat owners in HDB flats have until 31 August to register their "
            "cats under the new licensing scheme. Officials said the transition "
            "period is intended to give existing owners time to comply, and that "
            "enforcement is not the immediate focus."
        ),
        status_asserted=StatusType.DEADLINE,
        topic="cat-licensing",
        url_slug="news/cat-licensing-deadline",
    ),
]


# ---------------------------------------------------------------------------
# Cluster 2 — NS / Enlistment Act legal status (legal / Singapore)
#
# The ladder stops at CHARGE on purpose. There is no conviction document and no
# sentence document, so a forwarded claim of "convicted and sentenced to 3
# years" must come back as unsupported rather than confirmed.
# ---------------------------------------------------------------------------

NS_ENLISTMENT: list[Evidence] = [
    _doc(
        id="sg-spf-101",
        title="Man arrested on arrival at Changi Airport over NS obligations",
        publisher="Singapore Police Force",
        tier=SourceTier.OFFICIAL,
        jurisdiction=Jurisdiction.SINGAPORE,
        published_at="2026-03-11",
        snippet=(
            "A 27-year-old man was arrested at Changi Airport upon his arrival in "
            "Singapore in connection with offences under the Enlistment Act. He "
            "was taken in for investigation. Police investigations are ongoing."
        ),
        status_asserted=StatusType.ARREST,
        topic="ns-enlistment",
        url_slug="spf/changi-arrest-enlistment",
    ),
    _doc(
        id="sg-agc-102",
        title="Charges filed under the Enlistment Act",
        publisher="Attorney-General's Chambers",
        tier=SourceTier.OFFICIAL,
        jurisdiction=Jurisdiction.SINGAPORE,
        published_at="2026-03-14",
        snippet=(
            "The accused was charged in court with offences under section 33 of "
            "the Enlistment Act for remaining outside Singapore without a valid "
            "exit permit. The case has been adjourned for a further mention. "
            "No plea has been taken at this stage."
        ),
        status_asserted=StatusType.CHARGE,
        topic="ns-enlistment",
        url_slug="agc/enlistment-act-charges",
    ),
    _doc(
        id="sg-sso-103",
        title="Enlistment Act — penalties for failure to report for service",
        publisher="Singapore Statutes Online",
        tier=SourceTier.PRIMARY,
        jurisdiction=Jurisdiction.SINGAPORE,
        published_at="2025-11-02",
        snippet=(
            "A person guilty of an offence under this section shall be liable on "
            "conviction to a fine not exceeding $10,000 or to imprisonment for a "
            "term not exceeding 3 years or to both. The term stated is a maximum "
            "available to the court. Sentences are determined case by case having "
            "regard to the period of default and mitigating factors; imprisonment "
            "is not automatic."
        ),
        status_asserted=StatusType.PENALTY,
        topic="ns-enlistment",
        url_slug="sso/enlistment-act-s33",
    ),
    _doc(
        id="sg-mindef-104",
        title="MINDEF statement on defaulters returning to Singapore",
        publisher="Ministry of Defence",
        tier=SourceTier.OFFICIAL,
        jurisdiction=Jurisdiction.SINGAPORE,
        published_at="2026-02-20",
        snippet=(
            "Each case involving a person who has remained overseas without a "
            "valid exit permit is assessed on its own facts. Outcomes range from "
            "administrative action and fines to prosecution, depending on the "
            "length of default and the circumstances. It is not the case that "
            "every returning defaulter is prosecuted or imprisoned."
        ),
        status_asserted=StatusType.STATEMENT,
        topic="ns-enlistment",
        url_slug="mindef/defaulters-statement",
    ),
    _doc(
        id="sg-news-105",
        title="Man faces Enlistment Act charges after returning to Singapore",
        publisher="The Straits Times",
        tier=SourceTier.CREDIBLE_NEWS,
        jurisdiction=Jurisdiction.SINGAPORE,
        published_at="2026-03-15",
        snippet=(
            "The man appeared in court and faces charges under the Enlistment "
            "Act. The case was adjourned. He has not entered a plea, and no "
            "conviction has been recorded. The court has not passed sentence."
        ),
        status_asserted=StatusType.CHARGE,
        topic="ns-enlistment",
        url_slug="news/enlistment-charges-court",
    ),
]


# ---------------------------------------------------------------------------
# Cluster 3 — "Rocky" developing animal-welfare case (legal / Singapore)
#
# The ladder stops at INVESTIGATION + STATEMENT. There is no charge document.
# The forwarded claim asserts a charge and active court action, so the correct
# behaviour is to refuse to confirm it and show the gap on the timeline.
# ---------------------------------------------------------------------------

ROCKY_CASE: list[Evidence] = [
    _doc(
        id="sg-avs-201",
        title="AVS investigating circumstances of dog's death during operation",
        publisher="Animal & Veterinary Service (AVS), NParks",
        tier=SourceTier.OFFICIAL,
        jurisdiction=Jurisdiction.SINGAPORE,
        published_at="2026-07-28",
        snippet=(
            "AVS is investigating the circumstances surrounding the death of a "
            "dog during an operation. Investigations are ongoing and no "
            "conclusions have been reached. AVS is unable to comment further "
            "while the matter is under investigation."
        ),
        status_asserted=StatusType.INVESTIGATION,
        topic="rocky-case",
        url_slug="avs/investigation-dog-death",
    ),
    _doc(
        id="sg-avs-202",
        title="Statement on enforcement operation and animal welfare protocols",
        publisher="Animal & Veterinary Service (AVS), NParks",
        tier=SourceTier.OFFICIAL,
        jurisdiction=Jurisdiction.SINGAPORE,
        published_at="2026-08-04",
        snippet=(
            "The agency has completed its internal review of the handling "
            "procedures used during the operation. Findings have been referred "
            "for further consideration. The review examined the conduct of the "
            "officers involved as well as the circumstances of the animal's care."
        ),
        status_asserted=StatusType.STATEMENT,
        topic="rocky-case",
        url_slug="avs/enforcement-statement",
    ),
    _doc(
        id="sg-agc-203",
        title="Case referred to Attorney-General's Chambers for review",
        publisher="Attorney-General's Chambers",
        tier=SourceTier.OFFICIAL,
        jurisdiction=Jurisdiction.SINGAPORE,
        published_at="2026-08-08",
        snippet=(
            "Investigation papers have been submitted to the Attorney-General's "
            "Chambers, which is reviewing the material to determine whether any "
            "prosecution should be brought. A decision on charges has not been "
            "made. No person has been charged in relation to this matter."
        ),
        status_asserted=StatusType.INVESTIGATION,
        topic="rocky-case",
        url_slug="agc/case-under-review",
    ),
    _doc(
        id="sg-news-204",
        title="Questions raised over dog's death; agency says review under way",
        publisher="Channel NewsAsia",
        tier=SourceTier.CREDIBLE_NEWS,
        jurisdiction=Jurisdiction.SINGAPORE,
        published_at="2026-08-05",
        snippet=(
            "The case has drawn public attention, with petitions calling for "
            "accountability. The agency said a review is under way. It is not "
            "clear whether the owner, the officers involved, or any other party "
            "will face action. No charges have been filed to date."
        ),
        status_asserted=StatusType.INVESTIGATION,
        topic="rocky-case",
        url_slug="news/dog-death-review",
    ),
]


# ---------------------------------------------------------------------------
# Cluster 4 — Product safety recall (product_safety / Malaysia + overseas)
#
# Built to exercise the overseas_recall -> local_recall escalation: a recall
# genuinely happened, but in another market.
# ---------------------------------------------------------------------------

PRODUCT_RECALL: list[Evidence] = [
    _doc(
        id="my-kpdn-301",
        title="Statement on imported snack product following overseas recall",
        publisher="Ministry of Domestic Trade and Cost of Living (KPDN)",
        tier=SourceTier.OFFICIAL,
        jurisdiction=Jurisdiction.MALAYSIA,
        published_at="2026-07-15",
        snippet=(
            "The ministry is aware of a recall of a snack product issued by "
            "authorities in another country. The affected batches were not "
            "distributed in Malaysia. No recall has been issued locally. "
            "Consumers are advised to check batch numbers on imported products."
        ),
        status_asserted=StatusType.ADVISORY,
        topic="product-recall",
        url_slug="kpdn/imported-snack-statement",
    ),
    _doc(
        id="my-moh-302",
        title="Consumer advisory: imported food products and batch checking",
        publisher="Ministry of Health Malaysia",
        tier=SourceTier.OFFICIAL,
        jurisdiction=Jurisdiction.MALAYSIA,
        published_at="2026-07-16",
        snippet=(
            "An advisory has been issued reminding consumers to check batch "
            "codes on imported products. An advisory is not a ban. The product "
            "remains available for sale and has not been prohibited."
        ),
        status_asserted=StatusType.ADVISORY,
        topic="product-recall",
        url_slug="moh-my/consumer-advisory-imports",
    ),
    _doc(
        id="ov-fda-303",
        title="Overseas regulator announces voluntary recall of specific batches",
        publisher="Overseas food safety regulator",
        tier=SourceTier.OFFICIAL,
        jurisdiction=Jurisdiction.OVERSEAS,
        published_at="2026-07-12",
        snippet=(
            "A voluntary recall was announced covering specific production "
            "batches distributed within that market. The recall is limited to "
            "the domestic market of the issuing regulator and does not extend to "
            "products sold in Southeast Asia."
        ),
        status_asserted=StatusType.OVERSEAS_RECALL,
        topic="product-recall",
        url_slug="overseas/voluntary-recall-batches",
    ),
    _doc(
        id="my-news-304",
        title="Authorities: no local recall for snack product",
        publisher="The Star",
        tier=SourceTier.CREDIBLE_NEWS,
        jurisdiction=Jurisdiction.MALAYSIA,
        published_at="2026-07-17",
        snippet=(
            "Authorities clarified that the product has not been recalled in "
            "Malaysia and that the overseas recall covered batches not sold "
            "here. Messages circulating on social media claiming a nationwide "
            "ban are inaccurate."
        ),
        status_asserted=StatusType.ADVISORY,
        topic="product-recall",
        url_slug="news-my/no-local-recall",
    ),
]


# ---------------------------------------------------------------------------
# The store
# ---------------------------------------------------------------------------

ALL_EVIDENCE: list[Evidence] = [
    *CAT_LICENSING,
    *NS_ENLISTMENT,
    *ROCKY_CASE,
    *PRODUCT_RECALL,
]

EVIDENCE_BY_ID: dict[str, Evidence] = {doc.id: doc for doc in ALL_EVIDENCE}


def topic_of(doc: Evidence) -> str:
    """Cluster label, used for retrieval diagnostics only."""
    return getattr(doc, "_topic", "unknown")


def get_evidence(evidence_id: str) -> Evidence | None:
    return EVIDENCE_BY_ID.get(evidence_id)
