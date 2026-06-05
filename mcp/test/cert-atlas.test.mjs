// Unit tests for the Cert Atlas data layer. Run: npm test  (needs the build:
// node --test imports from dist/). Uses the bundled/local dataset.
import { test } from "node:test";
import assert from "node:assert/strict";
import { withUtm, practiceCta, toText, getIndex, resolveExam, getBlueprint } from "../dist/catalog.js";

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
