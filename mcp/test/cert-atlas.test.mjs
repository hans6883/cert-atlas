// Unit tests for the Cert Atlas data layer. Run: npm test  (needs the build:
// node --test imports from dist/). Uses the bundled/local dataset.
import { test } from "node:test";
import assert from "node:assert/strict";
import { withUtm, practiceCta, toText, getIndex, resolveExam, getBlueprint } from "../dist/catalog.js";
import { blueprintText, datasetSummary } from "../dist/server.js";

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
