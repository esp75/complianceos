# Verification log

How each part of the knowledge pack was checked, and what still needs a human. Every record is
`status: draft` until a licensing practitioner reviews it; see [CONTRIBUTING.md](../CONTRIBUTING.md)
to help.

Rule we follow: a citation's `excerpt` is copied from the legal text itself, never written from
memory or from a secondary summary. When an official site blocks automated access, we verify the
excerpt against an exact copy and say so here.

## Research pass of 2026-10-15

### ITU
- Radio Regulations, Edition of 2024, Volumes 1 and 3, downloaded from ITU's own digital
  collection (`search.itu.int`). Nos. 9.1, 9.2B, 9.30, 9.38, 11.25, 11.44, 11.44B, 11.44C and
  Resolution 35 (Rev.WRC-23) quoted from those PDFs.
- **Simplification to know about:** the planner chooses between advance publication and
  coordination from orbit and service. The real test depends on the exact bands (RR Nos. 9.7 to
  9.21); the licence text says so and tells users to confirm with their administration.

### France
- `legifrance.gouv.fr` refuses automated requests. The LOS (Law 2008-518) excerpts were checked
  against a Legifrance print of the version in force on 26 May 2024 (as amended by Law 2023-703).
  CPCE Articles L97-2 and R52-3-1 to R52-3-6 were checked against the codes.droit.org edition of
  10 October 2026, which is generated from the official DILA open data (last modification
  19 August 2026).
- CNES FSOA pages (`spacecare.cnes.fr`): authorisation process, 5-6 month lead time, contact form.
- ANFR guide for start-ups and SMEs (v1.0, 2021): `satcoord@anfr.fr`, process, ITU and
  ministerial fees.
- **Needs a human:** confirm each excerpt on Legifrance; confirm the EUR 20,000 ministerial
  authorisation fee is current (it comes from the 2021 guide).

### United Kingdom
- Space Industry Act 2018 ss.1 and 3, Outer Space Act 1986 ss.1-3, Wireless Telegraphy Act 2006
  s.8 and Communications Act 2003 s.22 from legislation.gov.uk (current revised text, XML).
- CAA orbital operator page: fee, assessment times, documents, `commercialspaceflight@caa.co.uk`.
- **Needs a human:** `ofcom.org.uk` refuses automated requests, so Ofcom's satellite filing
  procedures, fees, earth station licence types, processing times and contact channels are not
  yet captured. The Ofcom durations in the pack are estimates.

### Luxembourg
- Law of 15 December 2020 on space activities, from the official journal PDF (Mémorial A n° 1086)
  on the Legilux filestore.
- LSA legal framework page (6-month lead time, registry, 2025 fee regulation) and contact page.
- Electronic media law, Art. 20: quoted from the 2001 coordinated text in the official journal.
- **Needs a human:** check Art. 20 against the current consolidated text (later amendments); read
  the SMC space page (it timed out); add the amounts from the Grand-Ducal Regulation of
  11 July 2025 on fees.

### United States
- 47 CFR §§ 25.102, 25.121, 25.122, 25.137, 25.164 and 15 CFR §§ 960.2, 960.5, 960.7 from the eCFR
  API, current as of 13 October 2026.
- FCC Space Bureau and NOAA CRSRA pages for authority descriptions and contact pages.
- **Needs a human:** FCC processing times are estimates (no regulatory time limit).

### Facilitators
- Each firm's description is taken from its own website or publication, linked in `source`.
- Listing is neutral: no ranking and no paid placement. To be listed, corrected or removed, open
  an issue or pull request.

## Known gaps

- Earth station licensing in France and Luxembourg is not modelled yet.
- Launch licensing is only covered where it falls under the same authorisation (France's LOS); the
  UK launch operator licence and US FAA licensing are not modelled.
- National registration of space objects is only modelled for Luxembourg.
- Landing rights / market access for services outside the US are not modelled.
