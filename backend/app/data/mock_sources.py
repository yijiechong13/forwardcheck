"""Seeded evidence corpus.

EVERY DOCUMENT HERE IS HAND-WRITTEN SAMPLE DATA. Titles, snippets, and dates
resemble real advisories so the pipeline has something realistic to reason over,
but nothing was scraped and every URL is a labelled placeholder. `is_mock=True`
is set on all of them and surfaced in the UI.

Scope: Singapore only. The single Overseas document is deliberate and
load-bearing — the overseas-recall vs local-recall distinction is one of the
escalations this product exists to catch, and refuting "recalled in Singapore"
requires evidence that the recall happened somewhere else.

Design note — the *absences* are the point. Most clusters deliberately stop one
rung short of what the forwarded message claims:

  * ns-enlistment: arrest and charge exist; conviction and sentence do not.
  * rocky-case:    investigation and a statement exist; no charge does.
  * product-recall: an overseas batch recall and local advisories exist;
                    no Singapore recall and no ban do.
  * policy-stage:  consultation and passage exist; commencement and
                    enforcement do not.

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
# Cluster 4 — Product safety recall (product_safety / Singapore + overseas)
#
# Built to exercise two escalations at once:
#   overseas_recall -> local_recall  (a recall happened, but in another market)
#   affected batch  -> whole product (a real recall, over-scoped)
# The Singapore agencies issue an advisory, not a recall or a ban.
# ---------------------------------------------------------------------------

PRODUCT_RECALL: list[Evidence] = [
    _doc(
        id="sg-sfa-301",
        title="Advisory on imported snack product following overseas recall",
        publisher="Singapore Food Agency (SFA)",
        tier=SourceTier.OFFICIAL,
        jurisdiction=Jurisdiction.SINGAPORE,
        published_at="2026-07-15",
        snippet=(
            "SFA is aware of a recall of a snack product issued by authorities "
            "in another country. The affected batches were not imported into "
            "Singapore. No recall has been issued locally and the product has "
            "not been banned. Consumers are advised to check batch numbers on "
            "imported products."
        ),
        status_asserted=StatusType.ADVISORY,
        topic="product-recall",
        url_slug="sfa/imported-snack-advisory",
    ),
    _doc(
        id="sg-hsa-302",
        title="Consumer advisory: checking batch codes on imported products",
        publisher="Health Sciences Authority (HSA)",
        tier=SourceTier.OFFICIAL,
        jurisdiction=Jurisdiction.SINGAPORE,
        published_at="2026-07-16",
        snippet=(
            "An advisory has been issued reminding consumers to check batch "
            "codes on imported products. An advisory is not a ban. The product "
            "remains available for sale in Singapore and has not been "
            "prohibited or withdrawn."
        ),
        status_asserted=StatusType.ADVISORY,
        topic="product-recall",
        url_slug="hsa/consumer-advisory-imports",
    ),
    _doc(
        id="ov-reg-303",
        title="Overseas regulator announces voluntary recall of specific batches",
        publisher="Overseas food safety regulator",
        tier=SourceTier.OFFICIAL,
        jurisdiction=Jurisdiction.OVERSEAS,
        published_at="2026-07-12",
        snippet=(
            "A voluntary recall was announced covering three production batches "
            "distributed within that market. The recall is limited to the "
            "domestic market of the issuing regulator and to the batch codes "
            "listed. It does not extend to products sold in Singapore, and "
            "other batches of the same product are unaffected."
        ),
        status_asserted=StatusType.OVERSEAS_RECALL,
        topic="product-recall",
        url_slug="overseas/voluntary-recall-batches",
    ),
    _doc(
        id="sg-news-304",
        title="Authorities: no local recall for snack product",
        publisher="Channel NewsAsia",
        tier=SourceTier.CREDIBLE_NEWS,
        jurisdiction=Jurisdiction.SINGAPORE,
        published_at="2026-07-17",
        snippet=(
            "Authorities clarified that the product has not been recalled in "
            "Singapore and that the overseas recall covered batches not sold "
            "here. Messages circulating on social media claiming a nationwide "
            "ban are inaccurate. Only the batches listed by the overseas "
            "regulator are affected, not the whole product line."
        ),
        status_asserted=StatusType.ADVISORY,
        topic="product-recall",
        url_slug="news/no-local-recall",
    ),
]


# ---------------------------------------------------------------------------
# Cluster 5 — Workplace fairness legislation (policy / Singapore)
#
# The policy ladder stops at PASSED. The law has been passed but is not yet in
# force, so a forwarded claim that "fines start immediately" is asserting two
# rungs it has not reached (effective, enforced).
# ---------------------------------------------------------------------------

POLICY_STAGE: list[Evidence] = [
    _doc(
        id="sg-mom-401",
        title="Workplace fairness legislation passed in Parliament",
        publisher="Ministry of Manpower",
        tier=SourceTier.OFFICIAL,
        jurisdiction=Jurisdiction.SINGAPORE,
        published_at="2026-04-08",
        snippet=(
            "The Bill was passed in Parliament. The legislation will take "
            "effect at a later date to be announced, giving employers time to "
            "review their practices. Passing the Bill does not bring it into "
            "force, and the provisions are not yet operative."
        ),
        status_asserted=StatusType.PASSED,
        topic="policy-stage",
        url_slug="mom/workplace-fairness-passed",
    ),
    _doc(
        id="sg-mom-402",
        title="Implementation timeline and transition support for employers",
        publisher="Ministry of Manpower",
        tier=SourceTier.OFFICIAL,
        jurisdiction=Jurisdiction.SINGAPORE,
        published_at="2026-04-10",
        snippet=(
            "Employers will be given a transition period before the "
            "requirements apply. During this period the focus is on education "
            "and advisory support rather than enforcement. No penalties will "
            "be imposed before the commencement date, and enforcement action "
            "will not begin immediately upon passage."
        ),
        status_asserted=StatusType.PASSED,
        topic="policy-stage",
        url_slug="mom/implementation-timeline",
    ),
    _doc(
        id="sg-mom-403",
        title="Public consultation on workplace fairness proposals",
        publisher="Ministry of Manpower",
        tier=SourceTier.OFFICIAL,
        jurisdiction=Jurisdiction.SINGAPORE,
        published_at="2025-08-14",
        snippet=(
            "A public consultation was held on proposals to strengthen "
            "protections against workplace discrimination. Recommendations "
            "were accepted in principle ahead of legislation being drafted."
        ),
        status_asserted=StatusType.PROPOSED,
        topic="policy-stage",
        url_slug="mom/workplace-fairness-consultation",
    ),
    _doc(
        id="sg-news-404",
        title="What the new workplace fairness law means, and when it starts",
        publisher="The Straits Times",
        tier=SourceTier.CREDIBLE_NEWS,
        jurisdiction=Jurisdiction.SINGAPORE,
        published_at="2026-04-09",
        snippet=(
            "The law has been passed but is not yet in force. A commencement "
            "date has not been announced. Employers are not subject to "
            "penalties under the new provisions until the law commences."
        ),
        status_asserted=StatusType.PASSED,
        topic="policy-stage",
        url_slug="news/workplace-fairness-explainer",
    ),
]
# ---------------------------------------------------------------------------
# Cluster 6 — CDC vouchers (policy / Singapore)
#
# Tests SCOPE and MODALITY rather than status rung:
#   household -> every individual     (scope)
#   vouchers  -> cash                 (substance)
#   citizens  -> citizens and PRs     (eligibility scope)
# The amount and the scheme are real; almost everything around them is not.
# No document states a claim deadline, so that claim must abstain.
# ---------------------------------------------------------------------------

CDC_VOUCHERS: list[Evidence] = [
    _doc(
        id="sg-govsg-501",
        title="CDC Vouchers 2026: $500 for every Singaporean household",
        publisher="GovSG / Ministry of Finance",
        tier=SourceTier.OFFICIAL,
        jurisdiction=Jurisdiction.SINGAPORE,
        published_at="2026-01-03",
        snippet=(
            "Every Singaporean household will receive $500 in CDC Vouchers. "
            "The vouchers are allocated per household, not per individual, and "
            "one member of the household claims on the household's behalf. "
            "The vouchers may be used at participating heartland merchants, "
            "hawkers and supermarkets."
        ),
        status_asserted=StatusType.EFFECTIVE,
        topic="cdc-vouchers",
        url_slug="govsg/cdc-vouchers-2026",
    ),
    _doc(
        id="sg-govsg-502",
        title="CDC Vouchers: eligibility and how to claim",
        publisher="GovSG",
        tier=SourceTier.OFFICIAL,
        jurisdiction=Jurisdiction.SINGAPORE,
        published_at="2026-01-03",
        snippet=(
            "Singaporean households are eligible for the vouchers. Each "
            "household claims once. The vouchers are not a cash payout and "
            "cannot be withdrawn, transferred or exchanged for cash; they are "
            "digital vouchers redeemed at participating merchants."
        ),
        status_asserted=StatusType.ELIGIBILITY,
        topic="cdc-vouchers",
        url_slug="govsg/cdc-vouchers-eligibility",
    ),
    _doc(
        id="sg-govsg-503",
        title="Claim period for CDC Vouchers 2026",
        publisher="GovSG",
        tier=SourceTier.OFFICIAL,
        jurisdiction=Jurisdiction.SINGAPORE,
        published_at="2026-01-03",
        snippet=(
            "Vouchers remain valid until the stated expiry date at the end of "
            "the year. Households have the full validity period in which to "
            "claim and spend them. There is no requirement to claim within a "
            "single week."
        ),
        status_asserted=StatusType.DEADLINE,
        topic="cdc-vouchers",
        url_slug="govsg/cdc-vouchers-claim-period",
    ),
    _doc(
        id="sg-news-504",
        title="What to know about this year's CDC vouchers",
        publisher="Channel NewsAsia",
        tier=SourceTier.CREDIBLE_NEWS,
        jurisdiction=Jurisdiction.SINGAPORE,
        published_at="2026-01-04",
        snippet=(
            "The $500 is given per Singaporean household rather than to each "
            "person. Officials reminded the public that the vouchers are not "
            "cash and that messages claiming otherwise are inaccurate."
        ),
        status_asserted=StatusType.EFFECTIVE,
        topic="cdc-vouchers",
        url_slug="news/cdc-vouchers-explainer",
    ),
]


# ---------------------------------------------------------------------------
# Cluster 7 — Vaping / Kpod penalties (legal + policy / Singapore)
#
# Tests MODALITY hardest: the penalty regime genuinely changed, and the
# statutory maximum genuinely exists. The escalation is "up to, on conviction,
# for supply offences" -> "automatic, for anyone caught".
# ---------------------------------------------------------------------------

VAPING_PENALTIES: list[Evidence] = [
    _doc(
        id="sg-moh-601",
        title="Enhanced penalties for vaping offences take effect 1 May 2026",
        publisher="Ministry of Health / Health Sciences Authority",
        tier=SourceTier.OFFICIAL,
        jurisdiction=Jurisdiction.SINGAPORE,
        published_at="2026-04-20",
        snippet=(
            "Enhanced penalties for offences involving e-vaporisers take effect "
            "on 1 May 2026. The changes increase the maximum penalties available "
            "to the court, particularly for import, distribution and sale."
        ),
        status_asserted=StatusType.EFFECTIVE,
        topic="vaping-penalties",
        url_slug="moh/vaping-penalties-effective",
    ),
    _doc(
        id="sg-hsa-602",
        title="Penalties for possession and use of e-vaporisers",
        publisher="Health Sciences Authority",
        tier=SourceTier.OFFICIAL,
        jurisdiction=Jurisdiction.SINGAPORE,
        published_at="2026-04-20",
        snippet=(
            "Possession or use of an e-vaporiser is an offence and offenders "
            "are liable to a fine. Possession and use are dealt with by "
            "composition or a fine in the first instance and are treated "
            "differently from import, distribution and sale, which attract "
            "substantially heavier penalties including imprisonment."
        ),
        status_asserted=StatusType.PENALTY,
        topic="vaping-penalties",
        url_slug="hsa/vaping-possession-penalties",
    ),
    _doc(
        id="sg-sso-603",
        title="Statutory maximum penalties for e-vaporiser supply offences",
        publisher="Singapore Statutes Online",
        tier=SourceTier.PRIMARY,
        jurisdiction=Jurisdiction.SINGAPORE,
        published_at="2026-05-01",
        snippet=(
            "A person guilty of an offence relating to the import or "
            "distribution of prohibited tobacco products shall be liable on "
            "conviction to a fine or to imprisonment for a term not exceeding "
            "the stated maximum, or to both. The term stated is a maximum "
            "available to the court on conviction. Sentences are determined "
            "case by case; imprisonment is not automatic and does not follow "
            "from being caught in possession."
        ),
        status_asserted=StatusType.PENALTY,
        topic="vaping-penalties",
        url_slug="sso/tobacco-control-penalties",
    ),
    _doc(
        id="sg-hsa-604",
        title="Kpods and etomidate-laced vaporisers: enforcement approach",
        publisher="Health Sciences Authority",
        tier=SourceTier.OFFICIAL,
        jurisdiction=Jurisdiction.SINGAPORE,
        published_at="2026-04-25",
        snippet=(
            "Vaporisers containing controlled substances are treated more "
            "severely than standard e-vaporisers. Penalties differ by offence "
            "type and by the substance involved. Users identified may be "
            "referred for cessation or rehabilitation rather than prosecuted, "
            "depending on the circumstances."
        ),
        status_asserted=StatusType.ENFORCED,
        topic="vaping-penalties",
        url_slug="hsa/kpods-enforcement",
    ),
]


# ---------------------------------------------------------------------------
# Cluster 8 — Infant formula recall (product_safety / Singapore)
#
# A real recall, over-scoped. Specific batches of one product were recalled;
# the forward extends that to every product from two brands, and invents the
# reason. Tests: affected batch -> all products, and reason substitution.
# ---------------------------------------------------------------------------

FORMULA_RECALL: list[Evidence] = [
    _doc(
        id="sg-sfa-701",
        title="Recall of specific batches of infant milk formula powder",
        publisher="Singapore Food Agency (SFA)",
        tier=SourceTier.OFFICIAL,
        jurisdiction=Jurisdiction.SINGAPORE,
        published_at="2026-06-18",
        snippet=(
            "SFA has directed a recall of three specified batches of one infant "
            "milk formula powder product following a packaging integrity issue identified "
            "during routine checks. The recall is limited to the batch numbers "
            "and best-before dates listed. Other batches of the same product, "
            "and other products from the same brand, are not affected and "
            "remain on sale."
        ),
        status_asserted=StatusType.LOCAL_RECALL,
        topic="formula-recall",
        url_slug="sfa/infant-formula-batch-recall",
    ),
    _doc(
        id="sg-sfa-702",
        title="Affected infant milk powder batches: details and consumer guidance",
        publisher="Singapore Food Agency (SFA)",
        tier=SourceTier.OFFICIAL,
        jurisdiction=Jurisdiction.SINGAPORE,
        published_at="2026-06-18",
        snippet=(
            "Consumers who have purchased the affected milk powder batches may "
            "return them for a refund. Consumers are not advised to discard unaffected "
            "products. There is no evidence of toxin contamination; the recall "
            "was precautionary and related to packaging, not to the contents."
        ),
        status_asserted=StatusType.RECALL_SCOPE,
        topic="formula-recall",
        url_slug="sfa/infant-formula-affected-batches",
    ),
    _doc(
        id="sg-hsa-703",
        title="No safety concern identified for other infant milk powder brands",
        publisher="Health Sciences Authority",
        tier=SourceTier.OFFICIAL,
        jurisdiction=Jurisdiction.SINGAPORE,
        published_at="2026-06-20",
        snippet=(
            "Testing did not identify any contamination in other batches or "
            "in other brands of infant milk formula powder available in Singapore. No "
            "recall has been issued for other brands, and no brand-wide recall "
            "has been ordered."
        ),
        status_asserted=StatusType.ADVISORY,
        topic="formula-recall",
        url_slug="hsa/infant-formula-testing",
    ),
    _doc(
        id="sg-news-704",
        title="Only specific infant milk powder batches recalled in Singapore, agency clarifies",
        publisher="The Straits Times",
        tier=SourceTier.CREDIBLE_NEWS,
        jurisdiction=Jurisdiction.SINGAPORE,
        published_at="2026-06-19",
        snippet=(
            "The agency clarified that only the listed batches are affected, "
            "after messages circulated claiming all products from two brands "
            "had been recalled over toxins. Those claims are inaccurate."
        ),
        status_asserted=StatusType.RECALL_SCOPE,
        topic="formula-recall",
        url_slug="news/infant-formula-batches-clarified",
    ),
]


# ---------------------------------------------------------------------------
# Cluster 9 — Calamine lotion recall (product_safety / Singapore)
#
# Same shape as cluster 8 at a smaller scale: one affected batch of one
# product, forwarded as "all bottles". Included because batch-scope
# over-generalisation is the single most common product-safety forward, and
# one instance is not enough to show the pattern holds.
# ---------------------------------------------------------------------------

CALAMINE_RECALL: list[Evidence] = [
    _doc(
        id="sg-hsa-801",
        title="Recall of one batch of calamine lotion following heavy metal test",
        publisher="Health Sciences Authority",
        tier=SourceTier.OFFICIAL,
        jurisdiction=Jurisdiction.SINGAPORE,
        published_at="2026-05-09",
        snippet=(
            "HSA has recalled one batch of a calamine lotion product after "
            "testing detected cadmium above permissible limits in that batch. "
            "The recall applies to the single batch number listed. Other "
            "batches of the product tested within permissible limits and are "
            "not subject to recall."
        ),
        status_asserted=StatusType.LOCAL_RECALL,
        topic="calamine-recall",
        url_slug="hsa/calamine-batch-recall",
    ),
    _doc(
        id="sg-hsa-802",
        title="Consumer guidance: identifying the affected calamine batch",
        publisher="Health Sciences Authority",
        tier=SourceTier.OFFICIAL,
        jurisdiction=Jurisdiction.SINGAPORE,
        published_at="2026-05-09",
        snippet=(
            "Consumers should check the batch number printed on the bottle "
            "against the affected batch listed. Bottles from other batches do "
            "not need to be discarded. Consumers with the affected batch may "
            "return it to the point of purchase."
        ),
        status_asserted=StatusType.RECALL_SCOPE,
        topic="calamine-recall",
        url_slug="hsa/calamine-consumer-guidance",
    ),
    _doc(
        id="sg-news-803",
        title="One calamine lotion batch recalled over cadmium levels",
        publisher="Channel NewsAsia",
        tier=SourceTier.CREDIBLE_NEWS,
        jurisdiction=Jurisdiction.SINGAPORE,
        published_at="2026-05-10",
        snippet=(
            "The authority said the recall covers a single batch. Messages "
            "urging people to discard all bottles of the product go beyond "
            "what the recall states."
        ),
        status_asserted=StatusType.RECALL_SCOPE,
        topic="calamine-recall",
        url_slug="news/calamine-batch-recall",
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
    *POLICY_STAGE,
    *CDC_VOUCHERS,
    *VAPING_PENALTIES,
    *FORMULA_RECALL,
    *CALAMINE_RECALL,
]

EVIDENCE_BY_ID: dict[str, Evidence] = {doc.id: doc for doc in ALL_EVIDENCE}


def topic_of(doc: Evidence) -> str:
    """Cluster label, used for retrieval diagnostics only."""
    return getattr(doc, "_topic", "unknown")


def get_evidence(evidence_id: str) -> Evidence | None:
    return EVIDENCE_BY_ID.get(evidence_id)
