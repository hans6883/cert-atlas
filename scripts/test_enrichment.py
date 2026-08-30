import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from scripts.build_site import build_exam_page, build_vendor_page, _exam_page_title
from scripts.enrichment import (
    load_and_merge_overlay,
    merge_overlay,
    should_publish_exam,
    validate_overlay,
)
from scripts.bank_signals import aggregate_bank_signals
from scripts.generation_request import build_generation_request
from scripts.apply_enrichments import apply_enrichments


def rich_overlay(status="reviewed", publishable=True):
    return {
        "exam_id": "vendor-example-100",
        "editorial": {
            "meta_description": (
                "Understand the Example 100 exam scope, domain weighting, practical skills, "
                "preparation strategy, and source-verified objectives."
            ),
            "overview": (
                "The Example 100 credential validates practical judgment across planning, "
                "implementation, operations, and review. Candidates are expected to connect "
                "the published domains instead of treating them as isolated vocabulary lists. "
                "The blueprint emphasizes choosing an appropriate approach, recognizing tradeoffs, "
                "and applying documented controls in realistic situations. This overview is tied "
                "to the current official guide and avoids predicting unpublished questions or pass rates."
            ),
            "who_should_take": (
                "This exam is intended for practitioners who already perform supervised work in the "
                "field and now need to demonstrate consistent application of the vendor's documented process."
            ),
            "skills_summary": [
                "Plan work using the published lifecycle",
                "Apply controls to representative operating conditions",
                "Evaluate results and choose an appropriate corrective action",
            ],
            "preparation_strategy": (
                "Begin with the official objectives and map each objective to a concrete task you can "
                "perform or explain. Spend more time on weighted domains, but keep enough cross-domain "
                "practice to recognize dependencies. Use hands-on review for implementation skills and "
                "short retrieval sessions for terminology. Finish with mixed practice and review why an "
                "approach is appropriate, rather than memorizing isolated answer patterns from a question bank."
            ),
            "domain_guidance": [
                {
                    "domain_id": "1.0",
                    "summary": (
                        "Planning establishes the constraints and decision criteria used by every later "
                        "domain. Candidates should be able to translate requirements into an ordered, "
                        "verifiable approach and identify when missing information changes the decision."
                    ),
                    "study_focus": [
                        "Practice translating requirements into steps",
                        "Compare valid approaches using explicit constraints",
                    ],
                    "source_ids": ["official-guide"],
                }
            ],
            "exam_day_guidance": (
                "Confirm the current appointment and identification rules with the testing provider. "
                "During the exam, distinguish requirements stated in a scenario from assumptions that "
                "are not supported by the prompt."
            ),
            "source_ids": ["official-guide"],
        },
        "study_signals": {
            "topic_emphasis": [
                {"topic": "Planning", "level": "high", "share_percent": 18.5}
            ],
            "challenge_areas": ["Connecting planning decisions to later implementation choices"],
            "question_style_observations": ["Practice applying concepts across short scenarios"],
            "input_record_count": 240,
            "input_dataset_hash": "sha256:" + "b" * 64,
            "derivation": "aggregate_metadata_only",
            "official_weighting": False,
        },
        "fact_overrides": {
            "domains": [
                {
                    "domain_id": "1.0",
                    "weight_min_percent": 35,
                    "weight_max_percent": 45,
                    "source_ids": ["official-guide"],
                }
            ]
        },
        "sources": [
            {
                "id": "official-guide",
                "url": "https://vendor.example/exams/example-100/guide",
                "title": "Example 100 Official Exam Guide",
                "publisher": "Example Vendor",
                "source_type": "official_exam_guide",
                "accessed": "2026-08-25",
                "content_hash": "sha256:" + "a" * 64,
            }
        ],
        "quality": {
            "status": status,
            "publishable": publishable,
            "evidence_coverage": 0.95,
            "factual_confidence": 0.95,
            "generated_by": "test:model",
            "generated_at": "2026-08-25T00:00:00Z",
            "reviewed_at": "2026-08-25T01:00:00Z" if status == "reviewed" else None,
        },
    }


def retired_overlay():
    overlay = rich_overlay()
    overlay["study_signals"] = None
    overlay["lifecycle"] = {
        "status": "retired",
        "retired_on": "2026-06-30",
        "summary": (
            "Example Vendor retired EX-100 on June 30, 2026. New candidates should "
            "prepare for EX-101 instead; the historical blueprint remains here only "
            "to help prior learners understand which skills still transfer."
        ),
        "replacement": {
            "exam_code": "EX-101",
            "name": "Example Next Professional",
            "url": "https://vendor.example/exams/example-101",
            "study_guide_url": "https://vendor.example/exams/example-101/guide",
            "relationship": "direct_replacement",
        },
        "migration_actions": [
            "Stop scheduling or purchasing EX-100 preparation products.",
            "Compare the historical EX-100 domains with the current EX-101 blueprint.",
            "Rebuild the study plan around the current exam before taking practice tests.",
        ],
        "skill_comparison": [
            {
                "legacy_skill": "Planning",
                "legacy_weight": "35-45%",
                "replacement_skill": "Plan and operate",
                "replacement_weight": "40-50%",
                "change": "The replacement adds explicit operating and monitoring work.",
            }
        ],
        "source_ids": ["official-guide", "official-replacement"],
    }
    overlay["editorial"]["methodology"] = {
        "summary": (
            "Cert Atlas compared the dated official EX-100 and EX-101 guides at the "
            "domain and objective level. AI assisted with drafting and normalization; "
            "the published claims were checked against the linked vendor sources."
        ),
        "source_ids": ["official-guide", "official-replacement"],
    }
    overlay["sources"].append(
        {
            "id": "official-replacement",
            "url": "https://vendor.example/exams/example-101/guide",
            "title": "Example 101 Official Exam Guide",
            "publisher": "Example Vendor",
            "source_type": "official_exam_guide",
            "accessed": "2026-08-25",
            "content_hash": "sha256:" + "c" * 64,
        }
    )
    return overlay


def scheduled_retirement_overlay():
    overlay = retired_overlay()
    overlay["lifecycle"]["status"] = "scheduled_retirement"
    overlay["lifecycle"]["retires_on"] = "2026-08-31"
    overlay["lifecycle"].pop("retired_on")
    overlay["lifecycle"]["summary"] = (
        "Example Vendor will retire EX-100 on August 31, 2026. Candidates can "
        "still take the current exam before the cutoff, while new long-term "
        "study plans should use the EX-101 blueprint and current official guide."
    )
    overlay["lifecycle"]["migration_actions"] = [
        "Decide whether the remaining time is sufficient to complete EX-100 preparation.",
        "Use EX-101 for a study plan that extends beyond the retirement date.",
        "Recheck the official retirement list before scheduling because dates can change.",
    ]
    return overlay


def retired_without_replacement_overlay():
    overlay = retired_overlay()
    overlay["lifecycle"].pop("replacement")
    overlay["lifecycle"].pop("skill_comparison")
    overlay["lifecycle"]["summary"] = (
        "Example Vendor retired EX-100 on June 30, 2026. The reviewed official "
        "sources do not name a direct replacement, so this historical blueprint "
        "is preserved without inferring a successor or current registration path."
    )
    overlay["lifecycle"]["source_ids"] = ["official-guide"]
    overlay["editorial"]["methodology"]["source_ids"] = ["official-guide"]
    overlay["sources"] = [overlay["sources"][0]]
    return overlay


def base_exam():
    return {
        "exam_id": "vendor-example-100",
        "exam_name": "Example Professional",
        "exam_code": "EX-100",
        "certifying_body": "Example Vendor",
        "source_url": "https://vendor.example/exams/example-100",
        "domains": [
            {
                "id": "1.0",
                "name": "Planning",
                "weight_percent": 40,
                "objectives": [{"id": "1.1", "title": "Create a plan"}],
            }
        ],
        "practice_url": "https://quizforge.ai/tests/vendor-example-100",
    }


class EnrichmentValidationTests(unittest.TestCase):
    def test_reviewed_source_linked_overlay_is_publishable_and_merges(self):
        exam = base_exam()
        overlay = rich_overlay()

        result = validate_overlay(exam, overlay)

        self.assertTrue(result.publishable, result.errors)
        merged = merge_overlay(exam, overlay)
        self.assertEqual(merged["editorial"]["overview"], overlay["editorial"]["overview"])
        self.assertEqual(merged["content_quality"]["status"], "reviewed")
        self.assertIsNone(merged["domains"][0]["weight_percent"])
        self.assertEqual(merged["domains"][0]["weight_min_percent"], 35)
        self.assertEqual(merged["domains"][0]["weight_max_percent"], 45)

    def test_retired_exam_lifecycle_is_source_backed_and_merges(self):
        exam = base_exam()
        exam["study_signals"] = {"legacy": True}
        overlay = retired_overlay()

        result = validate_overlay(exam, overlay)
        merged = merge_overlay(exam, overlay)

        self.assertTrue(result.publishable, result.errors)
        self.assertEqual(merged["lifecycle"]["status"], "retired")
        self.assertEqual(merged["lifecycle"]["replacement"]["exam_code"], "EX-101")
        self.assertNotIn("study_signals", merged)

    def test_retired_exam_requires_valid_date_replacement_and_sources(self):
        exam = base_exam()
        overlay = retired_overlay()
        overlay["lifecycle"]["retired_on"] = "June 2026"
        overlay["lifecycle"]["replacement"]["url"] = "http://vendor.example/ex-101"
        overlay["lifecycle"]["source_ids"] = ["missing-source"]

        result = validate_overlay(exam, overlay)

        self.assertFalse(result.publishable)
        self.assertTrue(any("retired_on" in error for error in result.errors))
        self.assertTrue(any("replacement.url" in error for error in result.errors))
        self.assertTrue(any("missing-source" in error for error in result.errors))

    def test_retired_exam_rejects_unsupported_replacement_relationship(self):
        overlay = retired_overlay()
        overlay["lifecycle"]["replacement"]["relationship"] = "same_exam_renamed"

        result = validate_overlay(base_exam(), overlay)

        self.assertFalse(result.publishable)
        self.assertTrue(any("relationship" in error for error in result.errors))

    def test_scheduled_retirement_is_source_backed_and_publishable(self):
        result = validate_overlay(base_exam(), scheduled_retirement_overlay())

        self.assertTrue(result.publishable, result.errors)

    def test_scheduled_retirement_requires_retires_on(self):
        overlay = scheduled_retirement_overlay()
        overlay["lifecycle"].pop("retires_on")

        result = validate_overlay(base_exam(), overlay)

        self.assertFalse(result.publishable)
        self.assertTrue(any("retires_on" in error for error in result.errors))

    def test_invalid_lifecycle_status_does_not_emit_a_secondary_date_error(self):
        overlay = scheduled_retirement_overlay()
        overlay["lifecycle"]["status"] = "retiring_someday"

        result = validate_overlay(base_exam(), overlay)

        self.assertFalse(result.publishable)
        self.assertTrue(any("lifecycle.status" in error for error in result.errors))
        self.assertFalse(any("retired_on" in error for error in result.errors))

    def test_retired_exam_can_truthfully_omit_unverified_replacement(self):
        result = validate_overlay(base_exam(), retired_without_replacement_overlay())

        self.assertTrue(result.publishable, result.errors)

    def test_raw_exam_bank_shape_is_rejected(self):
        overlay = rich_overlay()
        overlay["study_signals"]["question_text"] = "Which answer is correct?"

        result = validate_overlay(base_exam(), overlay)

        self.assertFalse(result.publishable)
        self.assertTrue(any("question_text" in error for error in result.errors))

    def test_study_signals_cannot_claim_official_weighting(self):
        overlay = rich_overlay()
        overlay["study_signals"]["derivation"] = "aggregate_metadata_only"
        overlay["study_signals"]["official_weighting"] = True

        result = validate_overlay(base_exam(), overlay)

        self.assertFalse(result.publishable)
        self.assertTrue(any("official_weighting" in error for error in result.errors))

    def test_malformed_overlay_is_rejected_without_crashing_validation(self):
        overlay = rich_overlay()
        overlay["quality"]["evidence_coverage"] = "not-a-number"
        overlay["quality"]["generated_at"] = "yesterday"
        overlay["quality"]["reviewed_at"] = "today"
        overlay["editorial"]["domain_guidance"][0]["study_focus"] = None
        overlay["study_signals"]["topic_emphasis"] = None

        result = validate_overlay(base_exam(), overlay)

        self.assertFalse(result.publishable)
        self.assertTrue(any("evidence_coverage" in error for error in result.errors))
        self.assertTrue(any("generated_at" in error for error in result.errors))
        self.assertTrue(any("reviewed_at" in error for error in result.errors))

    def test_unknown_domain_and_source_reference_are_rejected(self):
        overlay = rich_overlay()
        guidance = overlay["editorial"]["domain_guidance"][0]
        guidance["domain_id"] = "9.9"
        guidance["source_ids"] = ["missing-source"]

        result = validate_overlay(base_exam(), overlay)

        self.assertFalse(result.publishable)
        self.assertTrue(any("9.9" in error for error in result.errors))
        self.assertTrue(any("missing-source" in error for error in result.errors))

    def test_invalid_weight_range_is_rejected(self):
        overlay = rich_overlay()
        override = overlay["fact_overrides"]["domains"][0]
        override["weight_min_percent"] = 60
        override["weight_max_percent"] = 40

        result = validate_overlay(base_exam(), overlay)

        self.assertFalse(result.publishable)
        self.assertTrue(any("weight range" in error for error in result.errors))

    def test_missing_or_truncated_meta_description_is_rejected(self):
        overlay = rich_overlay()
        overlay["editorial"]["meta_description"] = "Too short"

        result = validate_overlay(base_exam(), overlay)

        self.assertFalse(result.publishable)
        self.assertTrue(any("meta_description" in error for error in result.errors))

    def test_valid_faq_is_accepted_and_omitted_faq_still_validates(self):
        overlay = rich_overlay()
        overlay["editorial"]["faq"] = [
            {
                "question_title": "How many questions are on the EX-100 exam?",
                "answer_text": (
                    "The published guide describes a fixed-length form; candidates should "
                    "confirm the current count with Example Vendor before scheduling because "
                    "the blueprint is revised periodically and counts follow the revision."
                ),
            },
            {
                "question_title": "What is the passing score?",
                "answer_text": (
                    "The vendor publishes a scaled passing score rather than a raw percentage, "
                    "and the reviewed guide does not fix a universal number for every revision, "
                    "so candidates should verify the current threshold on the official page."
                ),
            },
            {
                "question_title": "How long is the exam?",
                "answer_text": (
                    "Timing follows the appointment slot booked with the testing provider, and "
                    "the official guide is the source of record for the current duration, so "
                    "candidates should confirm their seat time when scheduling the exam."
                ),
            },
            {
                "question_title": "What are the exam domains?",
                "answer_text": (
                    "The blueprint organizes the material into weighted domains beginning with "
                    "planning; each published domain carries objectives, and the weighting is "
                    "described on the page using the reviewed official guide as its source."
                ),
            },
        ]

        result = validate_overlay(base_exam(), overlay)
        legacy = validate_overlay(base_exam(), rich_overlay())

        self.assertTrue(result.publishable, result.errors)
        self.assertTrue(legacy.publishable, legacy.errors)  # faq stays optional

    def test_malformed_faq_is_rejected(self):
        overlay = rich_overlay()
        overlay["editorial"]["faq"] = [
            {"question_title": "How many questions are on the exam?", "answer_text": "Short."},
            {"question_title": "Is there a retake policy", "answer_text": "x " * 30},
            "not-an-object",
        ]

        result = validate_overlay(base_exam(), overlay)

        self.assertFalse(result.publishable)
        self.assertTrue(any("faq" in error for error in result.errors))

    def test_faq_cannot_use_exam_bank_keys(self):
        overlay = rich_overlay()
        overlay["editorial"]["faq"] = [
            {
                "question": "How many questions are on the EX-100 exam?",
                "answer": "x " * 30,
            }
        ] * 4

        result = validate_overlay(base_exam(), overlay)

        self.assertFalse(result.publishable)
        self.assertTrue(any("prohibited" in error for error in result.errors))

    def test_source_backed_objective_id_correction_is_applied(self):
        exam = base_exam()
        exam["domains"][0]["objectives"][0]["id"] = "1点1"
        overlay = rich_overlay()
        overlay["fact_overrides"]["objectives"] = [
            {
                "domain_id": "1.0",
                "objective_id": "1点1",
                "corrected_id": "1.1",
                "source_ids": ["official-guide"],
            }
        ]

        result = validate_overlay(exam, overlay)
        merged = merge_overlay(exam, overlay)

        self.assertTrue(result.publishable, result.errors)
        self.assertEqual(merged["domains"][0]["objectives"][0]["id"], "1.1")
        self.assertTrue(
            validate_overlay(merged, overlay).publishable,
            "source-backed corrections must be idempotent after the first apply",
        )

    def test_source_backed_domain_name_correction_is_applied(self):
        exam = base_exam()
        exam["domains"][0]["name"] = "Planning (35-45%)"
        overlay = rich_overlay()
        overlay["fact_overrides"]["domains"][0]["corrected_name"] = "Planning"

        result = validate_overlay(exam, overlay)
        merged = merge_overlay(exam, overlay)

        self.assertTrue(result.publishable, result.errors)
        self.assertEqual(merged["domains"][0]["name"], "Planning")
        self.assertTrue(validate_overlay(merged, overlay).publishable)

    def test_draft_overlay_cannot_merge_into_public_data(self):
        exam = base_exam()
        overlay = rich_overlay(status="draft", publishable=False)

        result = validate_overlay(exam, overlay)

        self.assertFalse(result.publishable)
        self.assertEqual(merge_overlay(exam, overlay), exam)

    def test_git_overlay_is_loaded_by_vendor_and_exam_id(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            overlay_path = root / "example-vendor" / "vendor-example-100.json"
            overlay_path.parent.mkdir()
            overlay_path.write_text(json.dumps(rich_overlay()), encoding="utf-8")

            merged, validation = load_and_merge_overlay(base_exam(), "example-vendor", root)

            self.assertIsNotNone(validation)
            self.assertTrue(validation.publishable, validation.errors)
            self.assertIn("editorial", merged)

    def test_new_registry_exam_requires_approved_enrichment_to_publish(self):
        exam = base_exam()

        self.assertFalse(should_publish_exam(exam, existing_exam_ids=set()))
        self.assertTrue(should_publish_exam(exam, existing_exam_ids={exam["exam_id"]}))
        self.assertTrue(
            should_publish_exam(merge_overlay(exam, rich_overlay()), existing_exam_ids=set())
        )


class EnrichedPageTests(unittest.TestCase):
    def test_page_renders_reviewed_editorial_and_visible_provenance(self):
        exam = merge_overlay(base_exam(), rich_overlay())
        html = build_exam_page("example-vendor", {"display_name": "Example Vendor"}, exam)

        self.assertIn("What This Exam Validates", html)
        self.assertIn("Who Should Take This Exam", html)
        self.assertIn("How to Prepare", html)
        self.assertIn("Planning: Study Guidance", html)
        self.assertIn("Sources and Verification", html)
        self.assertIn("Example 100 Official Exam Guide", html)
        self.assertIn("Verified 2026-08-25", html)
        self.assertIn("35-45%", html)
        self.assertIn("18.5% of practice metadata", html)
        self.assertIn(
            "<title>EX-100 Exam Guide, Domains &amp; Skills | Cert Atlas</title>", html
        )
        self.assertIn(".editorial {", html)
        self.assertIn(
            'meta name="description" content="Understand the Example 100 exam scope', html
        )
        self.assertNotIn("Which answer is correct?", html)

    def test_page_renders_faq_section_and_faqpage_schema(self):
        overlay = rich_overlay()
        overlay["editorial"]["faq"] = [
            {
                "question_title": "How many questions are on the EX-100 exam?",
                "answer_text": (
                    "Candidates should confirm the current count with Example Vendor because "
                    "the blueprint is revised periodically and the question count follows the "
                    "active revision rather than staying fixed across every published form."
                ),
            },
            {
                "question_title": "What is the passing score?",
                "answer_text": (
                    "The vendor publishes a scaled score rather than a raw percentage, and the "
                    "reviewed guide does not fix one threshold for every revision, so verify "
                    "the current requirement on the official certification page."
                ),
            },
            {
                "question_title": "How long is the exam?",
                "answer_text": (
                    "Timing follows the appointment slot booked with the testing provider and "
                    "the official guide is the source of record, so confirm seat time when the "
                    "appointment is scheduled rather than relying on older summaries."
                ),
            },
            {
                "question_title": "What are the exam domains?",
                "answer_text": (
                    "The blueprint organizes the material into weighted domains starting with "
                    "planning; every published domain carries objectives and the weighting is "
                    "described on this page using the reviewed official guide as its source."
                ),
            },
        ]
        exam = merge_overlay(base_exam(), overlay)
        html = build_exam_page("example-vendor", {"display_name": "Example Vendor"}, exam)

        self.assertIn("Frequently asked questions", html)
        self.assertIn("<h3>How many questions are on the EX-100 exam?</h3>", html)
        self.assertIn('<details class="faq-item">', html)
        self.assertIn('"@type": "FAQPage"', html)
        self.assertIn('"acceptedAnswer"', html)
        # Unenriched exam pages carry no FAQ schema or section.
        plain = build_exam_page("example-vendor", {"display_name": "Example Vendor"}, base_exam())
        self.assertNotIn("FAQPage", plain)
        self.assertNotIn("faq-item", plain)

    def test_page_does_not_render_unapproved_editorial(self):
        exam = base_exam()
        exam["editorial"] = rich_overlay(status="draft", publishable=False)["editorial"]
        exam["content_quality"] = {"status": "draft", "publishable": False}

        html = build_exam_page("example-vendor", {"display_name": "Example Vendor"}, exam)

        self.assertNotIn("What This Exam Validates", html)
        self.assertNotIn("Sources and Verification", html)
        self.assertNotIn(".editorial {", html)

    def test_retired_page_prioritizes_replacement_and_suppresses_stale_actions(self):
        exam = merge_overlay(base_exam(), retired_overlay())
        exam["exam_price_usd"] = 165
        exam["online_proctoring_available"] = True
        exam["question_types"] = ["Multiple Choice"]
        html = build_exam_page("example-vendor", {"display_name": "Example Vendor"}, exam)

        self.assertIn("EX-100 was retired on June 30, 2026", html)
        self.assertIn("EX-101", html)
        self.assertIn("What changed from EX-100 to EX-101", html)
        self.assertIn("How this page was made", html)
        self.assertIn("Historical EX-100 Domains", html)
        self.assertIn("EX-100 Retired: EX-101 Replacement &amp; Skill Map | Cert Atlas", html)
        self.assertIn('"@type": "WebPage"', html)
        self.assertNotIn('"@type": "Course"', html)
        self.assertNotIn("Register for this exam", html)
        self.assertNotIn("Practice Example Professional on QuizForge", html)
        self.assertNotIn("$165", html)
        self.assertNotIn("Online Proctoring", html)
        self.assertNotIn("Multiple Choice", html)

    def test_retired_page_labels_related_successor_without_calling_it_direct(self):
        overlay = retired_overlay()
        overlay["lifecycle"]["replacement"]["relationship"] = "related_successor"
        exam = merge_overlay(base_exam(), overlay)

        html = build_exam_page("example-vendor", {"display_name": "Example Vendor"}, exam)

        self.assertIn("Explore related current path EX-101", html)
        self.assertNotIn("Prepare for EX-101", html)

    def test_retired_page_title_keeps_replacement_info_within_seventy_chars(self):
        exam = merge_overlay(base_exam(), retired_overlay())
        exam["exam_code"] = ""
        exam["exam_name"] = "Microsoft Certified Azure Data Engineer Associate"

        title = _exam_page_title(exam)

        self.assertLessEqual(len(title), 70)
        self.assertTrue(title.endswith(" | Cert Atlas"))
        self.assertIn("Retired: EX-101", title)

    def test_scheduled_retirement_title_stays_within_seventy_chars(self):
        exam = merge_overlay(base_exam(), scheduled_retirement_overlay())
        exam["exam_code"] = ""
        exam["exam_name"] = "Microsoft Certified Azure Data Engineer Associate"

        title = _exam_page_title(exam)

        self.assertLessEqual(len(title), 70)
        self.assertTrue(title.endswith(" | Cert Atlas"))
        self.assertIn("Retires", title)

    def test_retired_page_replacement_without_url_renders_text_not_empty_href(self):
        # Null replacement urls exist in data/*.json (data-side defect; the overlay
        # validator rejects them, so simulate the published data shape directly).
        exam = merge_overlay(base_exam(), retired_overlay())
        exam["lifecycle"]["replacement"]["url"] = None

        html = build_exam_page("example-vendor", {"display_name": "Example Vendor"}, exam)

        self.assertNotIn('href=""', html)
        self.assertIn(
            '<span class="replacement-link">Prepare for EX-101: Example Next Professional</span>',
            html,
        )

    def test_scheduled_retirement_page_warns_without_disabling_current_exam(self):
        exam = merge_overlay(base_exam(), scheduled_retirement_overlay())

        html = build_exam_page("example-vendor", {"display_name": "Example Vendor"}, exam)

        self.assertIn("EX-100 retires on August 31, 2026", html)
        self.assertIn("Scheduled retirement", html)
        self.assertIn("Prepare for EX-101", html)
        self.assertIn("What This Exam Validates", html)
        self.assertIn("Practice Example Professional on QuizForge", html)
        self.assertIn("EX-100 Retires Aug 31: EX-101 Replacement", html)
        self.assertNotIn("Retired exam", html)
        self.assertNotIn("Historical EX-100 Scope", html)

    def test_retired_page_without_replacement_has_no_empty_successor_link(self):
        exam = merge_overlay(base_exam(), retired_without_replacement_overlay())

        html = build_exam_page("example-vendor", {"display_name": "Example Vendor"}, exam)

        self.assertIn("No direct replacement is named", html)
        self.assertIn("Retired: Blueprint &amp; Next Steps", html)
        self.assertNotIn('<a class="replacement-link"', html)
        self.assertNotIn("Practice Example Professional on QuizForge", html)

    def test_page_renders_string_objectives_from_official_sources(self):
        exam = base_exam()
        exam["domains"][0]["objectives"] = [
            "Configure an accounts payable operation",
            {"id": "1.2", "title": "Review an exception"},
        ]

        html = build_exam_page("example-vendor", {"display_name": "Example Vendor"}, exam)

        self.assertIn("Configure an accounts payable operation", html)
        self.assertIn("Review an exception", html)

    def test_vendor_page_labels_retired_exam_and_replacement(self):
        entry = {
            "exam_id": "vendor-example-100",
            "exam_name": "Example Professional",
            "exam_code": "EX-100",
            "domains": 1,
            "total_questions": 60,
            "duration_minutes": 90,
            "lifecycle_status": "retired",
            "retired_on": "2026-06-30",
            "replacement_exam_code": "EX-101",
            "replacement_url": "https://vendor.example/exams/example-101",
        }

        html = build_vendor_page(
            "example-vendor", {"display_name": "Example Vendor"}, [entry]
        )

        self.assertIn("Retired June 30, 2026", html)
        self.assertIn("replaced by EX-101", html)
        self.assertNotIn("60 questions", html)
        self.assertNotIn("90 min", html)

    def test_vendor_page_does_not_call_related_path_a_replacement(self):
        entry = {
            "exam_id": "vendor-example-100",
            "exam_name": "Example Professional",
            "exam_code": "EX-100",
            "domains": 1,
            "lifecycle_status": "retired",
            "retired_on": "2026-06-30",
            "replacement_exam_code": "EX-101",
            "replacement_relationship": "related_successor",
        }

        html = build_vendor_page(
            "example-vendor", {"display_name": "Example Vendor"}, [entry]
        )

        self.assertIn("related current path EX-101", html)
        self.assertNotIn("replaced by EX-101", html)

    def test_vendor_page_labels_scheduled_retirement(self):
        entry = {
            "exam_id": "vendor-example-100",
            "exam_name": "Example Professional",
            "exam_code": "EX-100",
            "domains": 1,
            "lifecycle_status": "scheduled_retirement",
            "retires_on": "2026-08-31",
            "replacement_exam_code": "EX-101",
            "replacement_relationship": "direct_replacement",
        }

        html = build_vendor_page(
            "example-vendor", {"display_name": "Example Vendor"}, [entry]
        )

        self.assertIn("Retires August 31, 2026", html)
        self.assertIn("will be replaced by EX-101", html)
        self.assertNotIn("Retired August", html)


class ApplyEnrichmentTests(unittest.TestCase):
    def test_applies_only_reviewed_overlay_and_updates_index_metadata(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            data_root = root / "data"
            enrichment_root = root / "enrichment"
            exam_path = data_root / "example-vendor" / "vendor-example-100.json"
            overlay_path = enrichment_root / "example-vendor" / "vendor-example-100.json"
            exam_path.parent.mkdir(parents=True)
            overlay_path.parent.mkdir(parents=True)
            exam_path.write_text(json.dumps(base_exam()), encoding="utf-8")
            overlay_path.write_text(json.dumps(rich_overlay()), encoding="utf-8")
            (data_root / "index.json").write_text(
                json.dumps(
                    {
                        "total_exams": 1,
                        "exams": [
                            {
                                "exam_id": "vendor-example-100",
                                "vendor_slug": "example-vendor",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            report = apply_enrichments(data_root, enrichment_root, write=True)

            applied = json.loads(exam_path.read_text(encoding="utf-8"))
            index = json.loads((data_root / "index.json").read_text(encoding="utf-8"))
            self.assertEqual(report["applied"], 1)
            self.assertEqual(applied["content_quality"]["status"], "reviewed")
            self.assertTrue(index["exams"][0]["enriched"])
            self.assertEqual(
                index["exams"][0]["verified_at"], "2026-08-25T01:00:00Z"
            )
            self.assertNotIn("content_status", index["exams"][0])

    def test_check_mode_does_not_write_and_reports_rejected_draft(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            data_root = root / "data"
            enrichment_root = root / "enrichment"
            exam_path = data_root / "example-vendor" / "vendor-example-100.json"
            overlay_path = enrichment_root / "example-vendor" / "vendor-example-100.json"
            exam_path.parent.mkdir(parents=True)
            overlay_path.parent.mkdir(parents=True)
            exam_path.write_text(json.dumps(base_exam()), encoding="utf-8")
            overlay_path.write_text(
                json.dumps(rich_overlay(status="draft", publishable=False)),
                encoding="utf-8",
            )
            (data_root / "index.json").write_text(
                json.dumps(
                    {
                        "total_exams": 1,
                        "exams": [
                            {
                                "exam_id": "vendor-example-100",
                                "vendor_slug": "example-vendor",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            report = apply_enrichments(data_root, enrichment_root, write=False)

            unchanged = json.loads(exam_path.read_text(encoding="utf-8"))
            self.assertEqual(report["rejected"], 1)
            self.assertNotIn("editorial", unchanged)

    def test_retirement_state_propagates_to_index_and_suppresses_practice_link(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            data_root = root / "data"
            enrichment_root = root / "enrichment"
            exam_path = data_root / "example-vendor" / "vendor-example-100.json"
            overlay_path = enrichment_root / "example-vendor" / "vendor-example-100.json"
            exam_path.parent.mkdir(parents=True)
            overlay_path.parent.mkdir(parents=True)
            exam_path.write_text(json.dumps(base_exam()), encoding="utf-8")
            overlay_path.write_text(json.dumps(retired_overlay()), encoding="utf-8")
            (data_root / "index.json").write_text(
                json.dumps(
                    {
                        "total_exams": 1,
                        "exams": [
                            {
                                "exam_id": "vendor-example-100",
                                "vendor_slug": "example-vendor",
                                "practice_url": "https://quizforge.ai/tests/example",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            report = apply_enrichments(data_root, enrichment_root, write=True)
            index = json.loads((data_root / "index.json").read_text(encoding="utf-8"))
            entry = index["exams"][0]

            self.assertEqual(report["applied"], 1)
            self.assertEqual(entry["lifecycle_status"], "retired")
            self.assertEqual(entry["retired_on"], "2026-06-30")
            self.assertEqual(entry["replacement_exam_code"], "EX-101")
            self.assertEqual(
                entry["replacement_relationship"], "direct_replacement"
            )
            self.assertEqual(
                entry["replacement_url"],
                "https://vendor.example/exams/example-101",
            )
            self.assertIsNone(entry["practice_url"])

    def test_scheduled_retirement_propagates_and_preserves_practice_link(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            data_root = root / "data"
            enrichment_root = root / "enrichment"
            exam_path = data_root / "example-vendor" / "vendor-example-100.json"
            overlay_path = enrichment_root / "example-vendor" / "vendor-example-100.json"
            exam_path.parent.mkdir(parents=True)
            overlay_path.parent.mkdir(parents=True)
            exam_path.write_text(json.dumps(base_exam()), encoding="utf-8")
            overlay_path.write_text(
                json.dumps(scheduled_retirement_overlay()), encoding="utf-8"
            )
            practice_url = "https://quizforge.ai/tests/example"
            (data_root / "index.json").write_text(
                json.dumps(
                    {
                        "total_exams": 1,
                        "exams": [
                            {
                                "exam_id": "vendor-example-100",
                                "vendor_slug": "example-vendor",
                                "practice_url": practice_url,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            report = apply_enrichments(data_root, enrichment_root, write=True)
            index = json.loads((data_root / "index.json").read_text(encoding="utf-8"))
            entry = index["exams"][0]

            self.assertEqual(report["applied"], 1)
            self.assertEqual(entry["lifecycle_status"], "scheduled_retirement")
            self.assertEqual(entry["retires_on"], "2026-08-31")
            self.assertEqual(entry["replacement_exam_code"], "EX-101")
            self.assertEqual(entry["practice_url"], practice_url)


class BankSignalTests(unittest.TestCase):
    def test_only_aggregate_metadata_leaves_the_private_bank(self):
        with tempfile.TemporaryDirectory() as temp:
            db_path = Path(temp) / "bank.db"
            connection = sqlite3.connect(db_path)
            connection.execute(
                """
                CREATE TABLE staged_questions (
                    exam_type_id INTEGER,
                    topic_name TEXT,
                    exam_category TEXT,
                    question_type TEXT,
                    difficulty TEXT,
                    text TEXT,
                    explanation TEXT
                )
                """
            )
            rows = [
                (7, "Planning", "Lifecycle", "scenario", "Hard", "PRIVATE STEM ONE", "PRIVATE EXPLANATION"),
                (7, "Planning", "Lifecycle", "scenario", "Medium", "PRIVATE STEM TWO", "PRIVATE EXPLANATION"),
                (7, "Operations", "Operations", "multiple_choice", "Easy", "PRIVATE STEM THREE", "PRIVATE EXPLANATION"),
                (8, "Other", "Other", "multiple_choice", "Easy", "UNRELATED PRIVATE STEM", "PRIVATE EXPLANATION"),
            ]
            connection.executemany(
                "INSERT INTO staged_questions VALUES (?, ?, ?, ?, ?, ?, ?)", rows
            )
            connection.commit()
            connection.close()

            signals = aggregate_bank_signals(db_path, exam_type_id=7)
            serialized = json.dumps(signals)

            self.assertEqual(signals["input_record_count"], 3)
            self.assertEqual(signals["topic_emphasis"][0]["topic"], "Planning")
            self.assertRegex(signals["input_dataset_hash"], r"^sha256:[0-9a-f]{64}$")
            self.assertNotIn("PRIVATE STEM", serialized)
            self.assertNotIn("PRIVATE EXPLANATION", serialized)
            self.assertNotIn("text", signals)
            self.assertNotIn("explanation", signals)

    def test_generation_request_combines_only_safe_evidence_and_signals(self):
        pack = {
            "exam": base_exam(),
            "sources": [{"id": "source-1", "text": "Official objectives and role profile."}],
            "generation_rules": {"bank_content_allowed": False},
        }
        signals = {
            "topic_emphasis": [{"topic": "Planning", "level": "high"}],
            "input_record_count": 3,
            "input_dataset_hash": "sha256:" + "c" * 64,
        }
        request = build_generation_request(
            pack,
            signals,
            system_prompt="Use official evidence only.",
            schema={"type": "object"},
        )
        serialized = json.dumps(request)

        self.assertEqual(request["response_format"]["type"], "json_schema")
        self.assertIn("Official objectives and role profile", serialized)
        self.assertIn("Planning", serialized)
        self.assertNotIn("question_text", serialized)
        self.assertNotIn("correct_answer", serialized)

    def test_signals_normalize_case_numeric_difficulty_and_common_item_types(self):
        with tempfile.TemporaryDirectory() as temp:
            db_path = Path(temp) / "bank.db"
            connection = sqlite3.connect(db_path)
            connection.execute(
                """
                CREATE TABLE staged_questions (
                    exam_type_id INTEGER,
                    topic_name TEXT,
                    exam_category TEXT,
                    question_type TEXT,
                    difficulty TEXT
                )
                """
            )
            connection.executemany(
                "INSERT INTO staged_questions VALUES (?, ?, ?, ?, ?)",
                [
                    (9, "Knowledge Mining", "Search", "mcq", "4"),
                    (9, "knowledge mining", "Search", "MCQ", "5"),
                ],
            )
            connection.commit()
            connection.close()

            signals = aggregate_bank_signals(db_path, exam_type_id=9)

            self.assertEqual(len(signals["topic_emphasis"]), 1)
            self.assertEqual(signals["topic_emphasis"][0]["share_percent"], 100.0)
            self.assertEqual(signals["difficulty_distribution"], {"hard": 2})
            self.assertIn("Knowledge Mining", signals["challenge_areas"][0])
            self.assertIn("Multiple-choice", signals["question_style_observations"][0])


if __name__ == "__main__":
    unittest.main()
