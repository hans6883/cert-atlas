# Reviewed enrichment overlays

This directory contains source-linked editorial overlays for public Cert Atlas records.

Path convention:

```text
enrichment/<vendor-slug>/<exam-id>.json
```

Only overlays with `quality.status = "reviewed"`, `quality.publishable = true`, and a passing result from `scripts/enrichment.py` are merged into public `data/` JSON. Drafts should be kept outside this directory or on a review branch.

Raw exam-bank content, model transcripts, evidence-pack text, private filesystem paths, and API responses do not belong here. Store temporary generation inputs under `.tmp/`, which is ignored by Git.

The publication flow is intentionally fail closed:

```powershell
python scripts/evidence_pack.py --exam-id <exam-id> --registry-db <registry.db> --source-root <source_material> --output .tmp/evidence/<exam-id>.json
python scripts/bank_signals.py --exam-id <exam-id> --bank-db <question-bank.db> --output .tmp/signals/<exam-id>.json
python scripts/generation_request.py --evidence .tmp/evidence/<exam-id>.json --signals .tmp/signals/<exam-id>.json --output .tmp/requests/<exam-id>.json
python scripts/apply_enrichments.py
python scripts/apply_enrichments.py --write
python scripts/build_site.py
```

The bank signal step selects only aggregate topic, category, style, and difficulty metadata. It never selects or exports question stems, choices, answers, or explanations. A model always produces a draft; a reviewed overlay is a separate Git decision.
