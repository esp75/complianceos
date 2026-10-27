# Why every requirement cites the law

A regulatory plan is only useful if you can check it. A list of licences with dates asks you to trust
the author. ComplianceOS asks you to check the text instead.

## What a citation carries

For each requirement the planner shows:

- the **instrument and article** it rests on;
- an **excerpt quoted verbatim** from the legal text, with an English rendering when the original
  is not in English;
- the **official URL**, so you can read the source yourself;
- the **date the text was checked**, so you can see how old the claim is.

Durations carry a label as well: *statutory* when a time limit is set in law, *practice* when it
comes from published guidance, and *estimate* otherwise. An estimate is shown as one.

## Why verbatim quotes

Paraphrase is where errors enter. A quote can be checked against the source in seconds, and a
paraphrase can drift from what the law says. The data rules require quotes to be copied, and
the validator checks that the citations resolve.

## The model cannot add a citation

The optional Claude summary is the one place a language model writes prose. Its text is checked
before it is shown: every paragraph must cite at least one source that already appears in the
roadmap, and it may not cite anything else. A paragraph that fails is rejected rather than
corrected silently, and the deterministic brief is kept.

This matters more than the summary's quality. A summary that sounds right but cites nothing
cannot be checked, so it is not shown.

## What this does not do

- It does not make a requirement correct. The records are `draft` until a licensing practitioner
  reviews them, and the verification status of each part is in
  [`knowledge/VERIFICATION.md`](../../knowledge/VERIFICATION.md).
- It is not legal advice. Confirm with the competent authority before acting.

If you find a citation that does not match its source, that is the most useful report you can make.
See [how to add or correct a jurisdiction](../how-to/add-or-correct-a-jurisdiction.md).
