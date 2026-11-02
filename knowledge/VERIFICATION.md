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

### Austria
- Weltraumgesetz (BGBl. I Nr. 132/2011) §§1, 3, 4, 5, 8 and Weltraumverordnung (BGBl. II Nr. 36/2015,
  as amended by BGBl. II Nr. 90/2018) §§2, 6, 8 read from the RIS open-data API
  (`data.bka.gv.at/ris/api`, per-paragraph XML) on 1 November 2026 and quoted from that text.
  `ris.bka.gv.at` itself refuses automated requests (HTTP 503), so the cited URLs are the
  consolidated-law pages for people; the Watch will report them unreachable until a fetchable
  route is found.
- Authority: the BMIMI "Weltraumbehörde" page (Department III/6) states that it approves and
  supervises space activities and keeps the register. The laws still name the "Bundesministerin/
  Bundesminister für Verkehr, Innovation und Technologie"; the ministry has been renamed.
  Named staff and direct lines are published on that page but deliberately not copied here.
- Timing: the six-month decision limit (§4(3)) is the only statutory figure. Preparation time is
  the planner's estimate.
- **Radio licence (added 2026-11-01):** excerpts for `at-radio-licence` were copied from the RIS API text of TKG 2021 (§ 4 Z 49, § 28(1), § 34(2), § 34(5)); the Fernmeldebüro site (fb.gv.at) was checked live. Fees, general authorisations (§ 28 ordinance), the 'no frequency coordination' case and satellite-specific procedure were not researched.
- **ITU route (checked 3 November 2026):** TKG 2021 §§ 13 to 20 and 28 to 35 and the Weltraumverordnung
  paragraphs 0 to 11 (current text, from the RIS API XML) were searched for satellite, orbit and ITU
  terms. None names an Austrian administration that files satellite networks with the ITU. The only
  ITU-specific rule is the operator's: WRV § 2(6) requires the operator to attach a licence or the
  documents needed for ITU frequency coordination, and WRG § 4(1) point 6 makes ITU compliance a
  condition of approval. Both are now cited in `at-space-activity-authorisation`. No licence record
  for an Austrian ITU filing was added, since no provision supports one.
- **Not covered:** the Weltraumregister
  procedure beyond the post-launch submission, and any sectoral approvals (e.g. Earth observation
  data rules). Germany is covered only as
  described under "Germany" below.
- **Needs a human:** confirm the BMIMI is the competent authority in practice and that §13
  (supervision, current version) and the fee in §8 have not been amended since 2018.

### Germany
- Telekommunikationsgesetz (TKG) §§ 91, 92 and 95, downloaded on 3 November 2026 from the official
  `gesetze-im-internet.de` XML (`/tkg_2021/xml.zip`, which can be fetched automatically) and quoted
  verbatim; the three cited section pages were checked live (HTTP 200).
- Authority: bundesnetzagentur.de checked live (HTTP 200). Only the website is recorded.
- Timing: the six-week decision limit (§ 91(4)) is the only statutory figure; international
  agreements on frequencies and orbital positions are expressly unaffected, so the plan's maximum
  is an estimate. The filing route (§ 95) has no statutory period; its figures are estimates.
- **Not covered:** any authorisation for the space activity itself, German registration of space
  objects, general assignments (Allgemeinzuteilungen) for earth stations, fees, the satellite data
  security law. Whether Germany has no general space law was not verified here.
- **Needs a human:** confirm with the Bundesnetzagentur how the § 95 transfer is applied for in
  practice.

### Netherlands
- Telecommunicatiewet (BWBR0009950), current text (validity date 3 November 2026), read from the
  official consolidated XML on repository.officiele-overheidspublicaties.nl. Article 3.13(1) is quoted
  verbatim. Article 3.13(2) and Articles 3.10 to 3.12 were read but not cited.
- Authority: the Rijksoverheid frequency-policy page names the RDI as the body that allocates
  frequency licences; the RDI home page (rdi.nl) was checked live.
- Timing: no decision period for a frequency licence was found in the statute text checked, so the
  plan's range is an estimate.
- **Not covered:** the Dutch ITU satellite filing route (the RDI international-coordination page is
  general and names no satellite procedure), licence-exempt use, fees, space-activity rules.
  Agentschap Telecom's domain does not resolve; the RDI now carries out the work.

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
