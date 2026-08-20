# ForwardCheck SG — Data Sources

> **MVP status:** every document bundled with ForwardCheck SG is **seeded mock evidence**,
> written by hand to resemble real advisories. URLs are placeholders. Nothing here was scraped,
> and no bundled snippet should be quoted as a real government statement.

## Scope

**Singapore only.** One jurisdiction means one controlled source hierarchy, which is what makes
tier weighting meaningful and evaluation tractable.

`Overseas` is retained as a jurisdiction but is not a second market — it exists so that an
overseas recall can be represented, because that is the evidence that refutes a claim of a
Singapore recall.

## Authority tiers

| Tier | Weight | Meaning |
|---|---|---|
| `primary` | 1.00 | The legal instrument itself — statutes, court records |
| `official` | 0.90 | The responsible Singapore agency stating its own position |
| `credible_news` | 0.65 | Established newsroom with a corrections policy |
| `secondary` | 0.30 | Blogs, aggregators, social posts, forwarded screenshots |

Retrieval scores are multiplied by tier weight, so an official advisory outranks a news
summary of that same advisory, which outranks a blog's summary of the news.

**Secondary and social sources are never proof.** They can show that a claim is circulating.
They cannot establish that it is true, and the pipeline must not resolve a claim on them alone.

## Singapore source hierarchy

### Official / primary

| Domain | Agency | Covers |
|---|---|---|
| sso.agc.gov.sg | Singapore Statutes Online | primary legislation, penalties |
| judiciary.gov.sg | Courts | hearings, convictions, sentences |
| gov.sg | Whole-of-government | policy announcements, clarifications |
| police.gov.sg | SPF | arrests, investigations, police statements |
| agc.gov.sg | AGC | prosecution decisions, charges |
| mha.gov.sg | MHA | home affairs policy |
| mom.gov.sg | MOM | employment, workplace legislation, work passes |
| ica.gov.sg | ICA | immigration, checkpoints |
| moh.gov.sg | MOH | health policy, disease advisories |
| hsa.gov.sg | HSA | product recalls, health product safety |
| sfa.gov.sg | SFA | food recalls and safety |
| nparks.gov.sg / avs.nparks.gov.sg | NParks / AVS | animal welfare, pet licensing |
| csa.gov.sg | CSA | cybersecurity advisories |
| mnd.gov.sg | MND | housing and national development |
| mindef.gov.sg | MINDEF | defence, NS obligations |
| mti.gov.sg | MTI | trade and industry |

### Credible news fallback

**CNA** · **The Straits Times** · **TODAY** · **Mothership** · **Mediacorp / Channel 8**

Used when no official source addresses a claim directly, or to establish that an official
statement was reported. Ranked below the agency's own page in every case.

### Not usable as proof

Social platforms, forwarded screenshots, blogs, content aggregators, and messaging channels.
`search_adapter.py` drops non-allowlisted domains rather than admitting them at a guessed tier —
an unknown source with an invented authority level corrupts the ranking every verdict rests on.

## Seeded evidence clusters

`backend/app/data/mock_sources.py` ships five clusters, one per demo claim plus a legal case:

1. **`cat-licensing`** (policy) — AVS/NParks pet cat licensing: the deadline, the cap per HDB
   flat, the *maximum* penalty under the Animals and Birds Act, grandfathering for existing
   owners, and community cats being out of scope.
2. **`ns-enlistment`** (legal) — arrest and charge are documented; conviction and sentence are
   **deliberately absent**, plus a statute stating a *maximum* penalty.
3. **`rocky-case`** (legal) — investigation opened, agency statement, case referred to AGC for
   review. **No charge document exists.**
4. **`product-recall`** (product safety) — an overseas batch recall, plus SFA and HSA advisories
   stating no local recall and no ban. **No Singapore recall document exists.**
5. **`policy-stage`** (policy) — consultation and passage in Parliament, plus a transition-period
   notice. **No commencement or enforcement document exists.**

The absences are the point. A verification system is only interesting if the evidence store can
fail to answer, and four of the five clusters are built so that the honest answer is partial.

## Adding a source later

1. Append an `EvidenceDoc` to the store (or a row in pgvector).
2. Set `tier`, `jurisdiction`, `publishedAt`, and `statusAsserted`.
3. Add the domain to `SOURCE_ALLOWLIST` in `search_adapter.py` with its tier.
4. Keep `isMock` accurate — flip to `False` only for genuinely retrieved documents.
