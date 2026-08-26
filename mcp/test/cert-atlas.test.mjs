// Unit tests for the Cert Atlas data layer. Run: npm test  (needs the build:
// node --test imports from dist/). Uses the bundled/local dataset.
import { test } from "node:test";
import assert from "node:assert/strict";
import { withUtm, practiceCta, toText, getIndex, resolveExam, getBlueprint } from "../dist/catalog.js";
import { blueprintText, datasetSummary, indexLine } from "../dist/server.js";

test("withUtm appends attribution and preserves existing query", () => {
  const u = new URL(withUtm("https://quizforge.ai/tests/cissp", "search_exams"));
  assert.equal(u.searchParams.get("utm_source"), "mcp");
  assert.equal(u.searchParams.get("utm_medium"), "cert_atlas");
  assert.equal(u.searchParams.get("utm_campaign"), "search_exams");

  const withQuery = new URL(withUtm("https://quizforge.ai/tests/x?ref=foo", "get_exam_blueprint"));
  assert.equal(withQuery.searchParams.get("ref"), "foo", "existing query preserved");
  assert.equal(withQuery.searchParams.get("utm_campaign"), "get_exam_blueprint");

  assert.equal(withUtm(null, "x"), null);
});

test("practiceCta is a single factual line", () => {
  assert.equal(
    practiceCta("CISSP", "https://quizforge.ai/tests/cissp?utm_source=mcp"),
    "Free practice exam for CISSP → https://quizforge.ai/tests/cissp?utm_source=mcp",
  );
});

test("toText flattens nested objects (retake_policy) preferring notes", () => {
  assert.equal(toText({ waiting_period_days: 14, notes: "14-day wait." }), "14-day wait.");
  assert.equal(toText(["a", "", "b"]), "a; b");
  assert.equal(toText(null), "");
});

test("index loads the full catalog", async () => {
  const { exams, meta } = await getIndex();
  assert.ok(exams.length > 1000, `expected >1000 exams, got ${exams.length}`);
  assert.ok(meta.total_vendors > 100);
});

test("resolveExam matches by code and by id, rejects garbage", async () => {
  const byCode = await resolveExam("CLF-C02");
  assert.ok(byCode, "CLF-C02 should resolve");
  assert.match(byCode.exam_id, /clf-c02/);
  assert.equal(await resolveExam("this exam does not exist xyz"), null);
});

test("get_exam_blueprint handles an exam with no domain breakdown", async () => {
  // CISSP ships domains: [] in the dataset — must not throw.
  const entry = await resolveExam("CISSP");
  if (entry) {
    const bp = await getBlueprint(entry);
    assert.ok(Array.isArray(bp.domains) || bp.domains == null);
  }
});

test("datasetSummary always uses current index metadata", () => {
  assert.equal(
    datasetSummary({ generated: "2026-08-25", total_exams: 2582, total_vendors: 260 }),
    "2,582 exams across 260 certifying bodies",
  );
});

test("get_exam_blueprint formatting includes only approved rich enrichment", () => {
  const entry = {
    exam_id: "vendor-example-100",
    exam_name: "Example Professional",
    exam_code: "EX-100",
    certifying_body: "Example Vendor",
    vendor_slug: "example-vendor",
    domains: 1,
    total_questions: 60,
    duration_minutes: 90,
    source_url: "https://vendor.example/exam",
    practice_url: "https://quizforge.ai/tests/example",
  };
  const blueprint = {
    ...entry,
    domains: [
      {
        id: "1.0",
        name: "Planning",
        weight_percent: null,
        weight_min_percent: 20,
        weight_max_percent: 25,
        objectives: [{ id: "1.1", title: "Create a source-backed plan" }],
      },
    ],
    editorial: {
      overview: "A source-grounded explanation of what the credential validates.",
      who_should_take: "Practitioners preparing to validate applied skills.",
      skills_summary: ["Plan work", "Apply controls", "Evaluate results"],
      preparation_strategy: "Map each published objective to a task and practice explaining tradeoffs.",
      domain_guidance: [
        {
          domain_id: "1.0",
          summary: "Planning establishes constraints used throughout the lifecycle.",
          study_focus: ["Translate requirements", "Compare approaches"],
        },
      ],
    },
    sources: [
      {
        id: "official-guide",
        url: "https://vendor.example/guide",
        title: "Official Exam Guide",
        publisher: "Example Vendor",
        source_type: "official_exam_guide",
        accessed: "2026-08-25",
      },
    ],
    content_quality: {
      status: "reviewed",
      publishable: true,
      evidence_coverage: 0.95,
      factual_confidence: 0.95,
      reviewed_at: "2026-08-25T01:00:00Z",
    },
    study_signals: {
      topic_emphasis: [{ topic: "Planning", level: "medium", share_percent: 18.5 }],
      challenge_areas: ["Higher-difficulty practice coverage includes Planning."],
      question_style_observations: ["Scenario items represent 20% of practice metadata."],
      input_record_count: 120,
      input_dataset_hash: `sha256:${"b".repeat(64)}`,
    },
  };

  const approved = blueprintText(entry, blueprint);
  assert.match(approved, /What this exam validates/);
  assert.match(approved, /Who should take it/);
  assert.match(approved, /How to prepare/);
  assert.match(approved, /Official Exam Guide/);
  assert.match(approved, /Verified: 2026-08-25/);
  assert.match(approved, /Planning.*20-25%/);
  assert.match(approved, /1\.1 Create a source-backed plan/);
  assert.match(approved, /Preparation signals/);
  assert.match(approved, /not official exam weights or predictions/);
  assert.match(approved, /Planning \(medium, 18.5%\)/);

  const draft = blueprintText(entry, {
    ...blueprint,
    content_quality: { ...blueprint.content_quality, status: "draft", publishable: false },
  });
  assert.doesNotMatch(draft, /What this exam validates/);
  assert.doesNotMatch(draft, /Official Exam Guide/);
});

test("retired blueprint leads with replacement and suppresses stale exam actions", () => {
  const entry = {
    exam_id: "vendor-example-100",
    exam_name: "Example Professional",
    exam_code: "EX-100",
    certifying_body: "Example Vendor",
    vendor_slug: "example-vendor",
    domains: 1,
    total_questions: 60,
    duration_minutes: 90,
    source_url: "https://vendor.example/exam",
    practice_url: "https://quizforge.ai/tests/example",
    lifecycle_status: "retired",
    retired_on: "2026-06-30",
    replacement_exam_code: "EX-101",
    replacement_url: "https://vendor.example/exams/example-101",
  };
  const blueprint = {
    ...entry,
    exam_price_usd: 165,
    question_types: ["Multiple Choice"],
    exam_registration_url: "https://vendor.example/register/ex-100",
    retake_policy: "Retake after 14 days.",
    practice_url: "https://quizforge.ai/tests/example",
    domains: [
      {
        id: "1.0",
        name: "Planning",
        weight_min_percent: 35,
        weight_max_percent: 45,
        objectives: [{ id: "1.1", title: "Create a historical plan" }],
      },
    ],
    editorial: {
      overview: "Historical EX-100 scope that remains useful for migration.",
      who_should_take: "Prior learners comparing their work with EX-101.",
      skills_summary: ["Reuse planning skills"],
      preparation_strategy: "Rebuild the plan around EX-101.",
      domain_guidance: [],
      exam_day_guidance: "Stale exam-day text that must not render.",
      methodology: {
        summary: "AI assisted with comparison; claims were reviewed against official sources.",
      },
    },
    lifecycle: {
      status: "retired",
      retired_on: "2026-06-30",
      summary: "EX-100 retired and EX-101 is the current replacement.",
      replacement: {
        exam_code: "EX-101",
        name: "Example Next Professional",
        url: "https://vendor.example/exams/example-101",
        study_guide_url: "https://vendor.example/exams/example-101/guide",
      },
      migration_actions: ["Use the EX-101 blueprint.", "Remap prior labs."],
      skill_comparison: [
        {
          legacy_skill: "Planning",
          legacy_weight: "35-45%",
          replacement_skill: "Plan and operate",
          replacement_weight: "40-50%",
          change: "Operations is now explicit.",
        },
      ],
    },
    sources: [
      {
        id: "official-guide",
        url: "https://vendor.example/guide",
        title: "Official EX-100 Guide",
        publisher: "Example Vendor",
        source_type: "official_exam_guide",
        accessed: "2026-08-25",
      },
    ],
    content_quality: {
      status: "reviewed",
      publishable: true,
      reviewed_at: "2026-08-26T04:00:00Z",
    },
  };

  const output = blueprintText(entry, blueprint);

  assert.match(output, /# Example Professional \(EX-100\) - Retired/);
  assert.match(output, /## Retirement and replacement/);
  assert.match(output, /EX-101/);
  assert.match(output, /## What changed from EX-100 to EX-101/);
  assert.match(output, /Planning \(35-45%\) -> Plan and operate \(40-50%\)/);
  assert.match(output, /## How this record was made/);
  assert.match(output, /## Historical domains/);
  assert.doesNotMatch(output, /Format:/);
  assert.doesNotMatch(output, /Price:/);
  assert.doesNotMatch(output, /Question types:/);
  assert.doesNotMatch(output, /Retake policy:/);
  assert.doesNotMatch(output, /Register:/);
  assert.doesNotMatch(output, /Free practice exam/);
  assert.doesNotMatch(output, /Stale exam-day text/);
});

test("published AI-102 data resolves as retired and points to AI-103", async () => {
  const entry = await resolveExam("AI-102");
  assert.ok(entry, "AI-102 should resolve");
  assert.equal(entry.lifecycle_status, "retired");
  assert.equal(entry.replacement_exam_code, "AI-103");
  assert.equal(entry.practice_url, null);

  const blueprint = await getBlueprint(entry);
  const output = blueprintText(entry, blueprint);
  assert.match(output, /AI-102.*Retired/);
  assert.match(output, /Replacement: AI-103/);
  assert.match(output, /What changed from AI-102 to AI-103/);
  assert.doesNotMatch(output, /Free practice exam/);
  assert.doesNotMatch(output, /Register:/);
});

test("published MB-240 data describes AB-250 as related rather than direct", async () => {
  const entry = await resolveExam("MB-240");
  assert.ok(entry, "MB-240 should resolve");
  assert.equal(entry.lifecycle_status, "retired");
  assert.equal(entry.replacement_exam_code, "AB-250");
  assert.equal(entry.replacement_relationship, "related_successor");
  assert.match(indexLine(entry, "search_exams"), /related current path AB-250/);
  assert.doesNotMatch(indexLine(entry, "search_exams"), /replaced by AB-250/);

  const blueprint = await getBlueprint(entry);
  assert.equal(blueprint.lifecycle.replacement.relationship, "related_successor");

  const output = blueprintText(entry, blueprint);
  assert.match(output, /Related current path: AB-250/);
  assert.match(output, /How MB-240 skills compare with AB-250/);
  assert.doesNotMatch(output, /Replacement: AB-250/);
  assert.doesNotMatch(output, /What changed from MB-240 to AB-250/);
});
