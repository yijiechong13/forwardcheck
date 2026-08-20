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

`backend/app/data/mock_sources.py` ships nine clusters (38 documents). Every document carries:
source title, publisher organisation, tier, jurisdiction, publication date, URL placeholder,
evidence snippet, and the status it asserts.

| Cluster | Domain | What it establishes — and what it deliberately does not |
|---|---|---|
| `cat-licensing` | policy | Licensing deadline and cap are real. The $5,000 is a **maximum on conviction**; existing owners keep their cats; community cats are out of scope. |
| `cdc-vouchers` | policy | $500 is real, **per household**, as vouchers not cash. **Silent on PR eligibility** and on any one-week deadline. |
| `vaping-penalties` | policy/legal | Penalty change from 1 May 2026 is real. Maximums are **available to the court**; possession is treated differently from supply. **No automatic jail.** |
| `formula-recall` | product safety | **Three specified batches** of one product, recalled for a **packaging defect**. Explicitly **no toxin contamination**, no brand-wide recall. |
| `calamine-recall` | product safety | **One batch** with cadmium above limits. Other batches tested within limits and **need not be discarded**. |
| `product-recall` | product safety | An overseas batch recall; SFA/HSA advisories. **No Singapore recall, no ban.** |
| `policy-stage` | policy | Consultation and passage in Parliament. **No commencement, no enforcement.** |
| `ns-enlistment` | legal | Arrest and charge documented. **No conviction, no sentence.** |
| `rocky-case` | legal | Investigation and agency statement; referred to AGC. **No charge.** |

The absences are the point, and the bolded negatives above are what most demo messages assert.
A verification system is only interesting if the evidence store can fail to answer — every
cluster is built so that at least one claim in its demo message must come back partial or
abstaining.

## Vocabulary note

Mock documents deliberately use the vocabulary real advisories use ("infant milk formula
powder", not just "infant formula"). This is realism rather than retrieval tuning: a real SFA
notice always names the product form, and a corpus that omits it makes lexical retrieval look
worse than it would be in production.

## Adding a source later

1. Append an `EvidenceDoc` to the store (or a row in pgvector).
2. Set `tier`, `jurisdiction`, `publishedAt`, and `statusAsserted`.
3. Add the domain to `SOURCE_ALLOWLIST` in `search_adapter.py` with its tier.
4. Keep `isMock` accurate — flip to `False` only for genuinely retrieved documents.
