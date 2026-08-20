# ForwardCheck — Data Sources

> **MVP status:** every document bundled with ForwardCheck is **seeded mock evidence**, written
> by hand to resemble real advisories. URLs are placeholders. Nothing here was scraped, and no
> bundled snippet should be quoted as a real government statement.

## Authority tiers

| Tier | Weight | Meaning |
|---|---|---|
| `primary` | 1.00 | The legal instrument itself — statutes, court records, gazette notices |
| `official` | 0.90 | The responsible agency stating its own position |
| `credible_news` | 0.65 | Established newsroom with corrections policy |
| `secondary` | 0.30 | Blogs, aggregators, social posts, forwarded screenshots |

Retrieval scores are multiplied by tier weight, so an official advisory outranks a news
summary of that same advisory, which outranks a blog's summary of the news.

## Singapore — sources to support

| Domain | Agency | Covers |
|---|---|---|
| gov.sg | Whole-of-government | policy announcements, factually.gov.sg clarifications |
| police.gov.sg | SPF | arrests, investigations, police statements |
| judiciary.gov.sg | Courts | hearings, convictions, sentences |
| agc.gov.sg | AGC | prosecution decisions, charges |
| mha.gov.sg | MHA | home affairs policy |
| mom.gov.sg | MOM | employment, work passes |
| ica.gov.sg | ICA | immigration, checkpoints |
| moh.gov.sg | MOH | health policy, disease advisories |
| hsa.gov.sg | HSA | product recalls, health product safety |
| sfa.gov.sg | SFA | food recalls and safety |
| nparks.gov.sg / avs.nparks.gov.sg | NParks / AVS | animal welfare, pet licensing |
| csa.gov.sg | CSA | cybersecurity advisories |
| scamshield.gov.sg | ScamShield | scam alerts |
| sso.agc.gov.sg | Singapore Statutes Online | primary legislation |

## Malaysia — sources to support

| Domain | Agency | Covers |
|---|---|---|
| pdrm.gov.my | PDRM | arrests, investigations |
| judiciary.gov.my | Courts | charges, convictions |
| kpdn.gov.my | KPDN | trade, pricing, consumer enforcement |
| moh.gov.my / myhealth | MOH | health advisories, product safety |
| Ministry pages | Various | policy status |

Credible Malaysian news: **Bernama**, **The Star**, **New Straits Times**, **Malay Mail**,
**Free Malaysia Today**.

## Seeded evidence sets

`backend/app/data/mock_sources.py` ships three evidence clusters matching the demo claims:

1. **`cat-licensing`** — AVS/NParks-style pet cat licensing scheme: licensing deadline, cap on
   cats per HDB flat, the *maximum* penalty under the Animals and Birds Act, the transition
   approach for existing owners, and community cat handling.
2. **`ns-enlistment`** — a legal-status cluster designed to stop one rung short of the forwarded
   claim: arrest and charge are documented, conviction and sentence are **deliberately absent**,
   plus a statute doc stating a *maximum* penalty.
3. **`rocky-case`** — a developing-news cluster: investigation opened, agency statement, case
   referred for prosecutorial review. No charge document exists.

The absences are the point. A verification system is only interesting if the evidence store can
fail to answer, and clusters 2 and 3 are built so that the honest answer is partial.

## Adding a source later

1. Append an `EvidenceDoc` to the store (or a row in pgvector).
2. Set `tier`, `jurisdiction`, `publishedAt`, and `statusAsserted`.
3. Keep `isMock` accurate — flip to `False` only for genuinely retrieved documents.
