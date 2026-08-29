#!/usr/bin/env python3
"""Validation and merge helpers for public Cert Atlas editorial enrichment."""

from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


PROHIBITED_BANK_KEYS = {
    "answer",
    "answer_choices",
    "answer_description",
    "answers",
    "choices",
    "choices_json",
    "correct",
    "correct_answer",
    "correct_answers",
    "explanation",
    "explanation_link",
    "llm_explanation",
    "question",
    "question_id",
    "question_text",
    "raw_question",
    "sample_question",
    "sample_questions",
    "stem",
}

OFFICIAL_SOURCE_TYPES = {
    "official_exam_guide",
    "official_objectives",
    "official_certification_page",
    "official_candidate_handbook",
    "official_registration_page",
    "official_renewal_guide",
    "official_documentation",
}

SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$", re.I)


def is_prohibited_bank_key(key: Any) -> bool:
    normalized = str(key).strip().lower()
    return normalized in PROHIBITED_BANK_KEYS or "sample_question" in normalized


@dataclass
class ValidationResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def publishable(self) -> bool:
        return not self.errors


def _word_count(value: Any) -> int:
    return len(re.findall(r"\b[\w'-]+\b", str(value or "")))


def _find_prohibited_keys(value: Any, path: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).strip().lower()
            child_path = f"{path}.{key}" if path else str(key)
            if is_prohibited_bank_key(normalized):
                found.append(child_path)
            found.extend(_find_prohibited_keys(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_find_prohibited_keys(child, f"{path}[{index}]"))
    return found


def _is_https_url(value: Any) -> bool:
    try:
        parsed = urlparse(str(value))
        return parsed.scheme == "https" and bool(parsed.netloc)
    except ValueError:
        return False


def _valid_iso_date(value: Any) -> bool:
    try:
        date.fromisoformat(str(value))
        return True
    except (TypeError, ValueError):
        return False


def _valid_iso_datetime(value: Any) -> bool:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.tzinfo is not None
    except (TypeError, ValueError):
        return False


def validate_overlay(exam: dict[str, Any], overlay: dict[str, Any]) -> ValidationResult:
    """Validate whether an overlay is safe and substantive enough to publish."""
    result = ValidationResult()

    if not isinstance(overlay, dict):
        result.errors.append("overlay must be a JSON object")
        return result

    prohibited = _find_prohibited_keys(overlay)
    result.errors.extend(f"prohibited exam-bank field: {path}" for path in prohibited)

    exam_id = str(exam.get("exam_id") or "")
    if overlay.get("exam_id") != exam_id:
        result.errors.append(
            f"overlay exam_id {overlay.get('exam_id')!r} does not match {exam_id!r}"
        )

    quality = overlay.get("quality")
    if not isinstance(quality, dict):
        result.errors.append("quality must be an object")
        quality = {}
    if quality.get("status") != "reviewed":
        result.errors.append("quality.status must be reviewed")
    if quality.get("publishable") is not True:
        result.errors.append("quality.publishable must be true")
    for metric in ("evidence_coverage", "factual_confidence"):
        value = quality.get(metric)
        try:
            valid_metric = not isinstance(value, bool) and float(value) >= 0.8
        except (TypeError, ValueError):
            valid_metric = False
        if not valid_metric:
            result.errors.append(f"quality.{metric} must be numeric and at least 0.8")
    if not str(quality.get("generated_by") or "").strip():
        result.errors.append("quality.generated_by is required")
    if not _valid_iso_datetime(quality.get("generated_at")):
        result.errors.append("quality.generated_at must be an ISO date-time with timezone")
    if not _valid_iso_datetime(quality.get("reviewed_at")):
        result.errors.append("quality.reviewed_at must be an ISO date-time with timezone")

    sources = overlay.get("sources")
    if not isinstance(sources, list) or not sources:
        result.errors.append("at least one source is required")
        sources = []

    source_ids: set[str] = set()
    official_sources = 0
    for index, source in enumerate(sources):
        prefix = f"sources[{index}]"
        if not isinstance(source, dict):
            result.errors.append(f"{prefix} must be an object")
            continue
        source_id = str(source.get("id") or "").strip()
        if not source_id:
            result.errors.append(f"{prefix}.id is required")
        elif source_id in source_ids:
            result.errors.append(f"duplicate source id: {source_id}")
        else:
            source_ids.add(source_id)
        if not _is_https_url(source.get("url")):
            result.errors.append(f"{prefix}.url must be an https URL")
        if not str(source.get("title") or "").strip():
            result.errors.append(f"{prefix}.title is required")
        if not str(source.get("publisher") or "").strip():
            result.errors.append(f"{prefix}.publisher is required")
        if source.get("source_type") in OFFICIAL_SOURCE_TYPES:
            official_sources += 1
        if not _valid_iso_date(source.get("accessed")):
            result.errors.append(f"{prefix}.accessed must be an ISO date")
        if not SHA256_PATTERN.match(str(source.get("content_hash") or "")):
            result.errors.append(f"{prefix}.content_hash must be sha256:<64 hex chars>")
    if sources and official_sources == 0:
        result.errors.append("at least one official source is required")

    editorial = overlay.get("editorial")
    if not isinstance(editorial, dict):
        result.errors.append("editorial must be an object")
        editorial = {}

    meta_description = str(editorial.get("meta_description") or "").strip()
    if _word_count(meta_description) < 12 or len(meta_description) > 160:
        result.errors.append(
            "editorial.meta_description must contain at least 12 words and at most 160 characters"
        )

    length_requirements = {
        "overview": 45,
        "who_should_take": 20,
        "preparation_strategy": 40,
        "exam_day_guidance": 20,
    }
    for field_name, minimum in length_requirements.items():
        count = _word_count(editorial.get(field_name))
        if count < minimum:
            result.errors.append(
                f"editorial.{field_name} must contain at least {minimum} words (got {count})"
            )

    skills = editorial.get("skills_summary")
    if not isinstance(skills, list) or len([item for item in skills if str(item).strip()]) < 3:
        result.errors.append("editorial.skills_summary must contain at least 3 items")

    editorial_source_ids = editorial.get("source_ids")
    if not isinstance(editorial_source_ids, list) or not editorial_source_ids:
        result.errors.append("editorial.source_ids must reference supporting sources")
    else:
        for source_id in editorial_source_ids:
            if source_id not in source_ids:
                result.errors.append(f"unknown source reference: {source_id}")

    exam_domain_ids = {
        str(domain.get("id"))
        for domain in exam.get("domains", [])
        if isinstance(domain, dict) and domain.get("id") is not None
    }
    guidance = editorial.get("domain_guidance")
    if not isinstance(guidance, list) or not guidance:
        result.errors.append("editorial.domain_guidance must contain at least one domain")
        guidance = []
    for index, item in enumerate(guidance):
        prefix = f"editorial.domain_guidance[{index}]"
        if not isinstance(item, dict):
            result.errors.append(f"{prefix} must be an object")
            continue
        domain_id = str(item.get("domain_id") or "")
        if domain_id not in exam_domain_ids:
            result.errors.append(f"unknown domain_id: {domain_id}")
        if _word_count(item.get("summary")) < 25:
            result.errors.append(f"{prefix}.summary must contain at least 25 words")
        study_focus = item.get("study_focus")
        if not isinstance(study_focus, list) or len(study_focus) < 2:
            result.errors.append(f"{prefix}.study_focus must contain at least 2 items")
        refs = item.get("source_ids")
        if not isinstance(refs, list) or not refs:
            result.errors.append(f"{prefix}.source_ids is required")
        else:
            for source_id in refs:
                if source_id not in source_ids:
                    result.errors.append(f"unknown source reference: {source_id}")

    faq = editorial.get("faq")
    if faq is not None:
        # Optional so legacy overlays without an FAQ block still validate. Entry keys are
        # deliberately question_title/answer_text: the literal keys "question" and "answer"
        # are prohibited exam-bank fields and are rejected by the scan above.
        if not isinstance(faq, list) or not 4 <= len(faq) <= 8:
            result.errors.append(
                "editorial.faq must contain between 4 and 8 items when present"
            )
            faq = []
        for index, item in enumerate(faq):
            prefix = f"editorial.faq[{index}]"
            if not isinstance(item, dict):
                result.errors.append(f"{prefix} must be an object")
                continue
            question = str(item.get("question_title") or "").strip()
            if not question:
                result.errors.append(f"{prefix}.question_title is required")
            elif not question.endswith("?"):
                result.errors.append(
                    f"{prefix}.question_title must end with a question mark"
                )
            if _word_count(item.get("answer_text")) < 25:
                result.errors.append(
                    f"{prefix}.answer_text must contain at least 25 words"
                )

    fact_overrides = overlay.get("fact_overrides")
    if fact_overrides is not None:
        if not isinstance(fact_overrides, dict):
            result.errors.append("fact_overrides must be an object")
        else:
            domain_overrides = fact_overrides.get("domains", [])
            if not isinstance(domain_overrides, list):
                result.errors.append("fact_overrides.domains must be an array")
                domain_overrides = []
            for index, item in enumerate(domain_overrides):
                prefix = f"fact_overrides.domains[{index}]"
                if not isinstance(item, dict):
                    result.errors.append(f"{prefix} must be an object")
                    continue
                domain_id = str(item.get("domain_id") or "")
                if domain_id not in exam_domain_ids:
                    result.errors.append(f"unknown domain_id: {domain_id}")
                if "corrected_name" in item and _word_count(
                    item.get("corrected_name")
                ) < 1:
                    result.errors.append(
                        f"{prefix}.corrected_name must not be empty"
                    )
                minimum = item.get("weight_min_percent")
                maximum = item.get("weight_max_percent")
                if not isinstance(minimum, (int, float)) or not isinstance(maximum, (int, float)):
                    result.errors.append(f"{prefix} weight range must contain numeric minimum and maximum")
                elif minimum < 0 or maximum > 100 or minimum > maximum:
                    result.errors.append(f"{prefix} has an invalid weight range")
                refs = item.get("source_ids")
                if not isinstance(refs, list) or not refs:
                    result.errors.append(f"{prefix}.source_ids is required")
                else:
                    for source_id in refs:
                        if source_id not in source_ids:
                            result.errors.append(f"unknown source reference: {source_id}")

            objectives_by_domain = {
                str(domain.get("id") or ""): {
                    str(objective.get("id") or "")
                    for objective in domain.get("objectives", [])
                    if isinstance(objective, dict)
                }
                for domain in exam.get("domains", [])
                if isinstance(domain, dict)
            }
            objective_overrides = fact_overrides.get("objectives", [])
            if not isinstance(objective_overrides, list):
                result.errors.append("fact_overrides.objectives must be an array")
                objective_overrides = []
            for index, item in enumerate(objective_overrides):
                prefix = f"fact_overrides.objectives[{index}]"
                if not isinstance(item, dict):
                    result.errors.append(f"{prefix} must be an object")
                    continue
                domain_id = str(item.get("domain_id") or "")
                objective_id = str(item.get("objective_id") or "")
                corrected_id = str(item.get("corrected_id") or "")
                known_objectives = objectives_by_domain.get(domain_id, set())
                if objective_id not in known_objectives and corrected_id not in known_objectives:
                    result.errors.append(
                        f"{prefix} references unknown objective {domain_id}/{objective_id}"
                    )
                if not re.match(r"^[A-Za-z0-9]+(?:[.\-][A-Za-z0-9]+)*$", corrected_id):
                    result.errors.append(f"{prefix}.corrected_id has an invalid format")
                refs = item.get("source_ids")
                if not isinstance(refs, list) or not refs:
                    result.errors.append(f"{prefix}.source_ids is required")
                else:
                    for source_id in refs:
                        if source_id not in source_ids:
                            result.errors.append(f"unknown source reference: {source_id}")

    skill_values = skills if isinstance(skills, list) else []
    total_editorial_words = sum(
        _word_count(editorial.get(field_name)) for field_name in length_requirements
    ) + sum(_word_count(item) for item in skill_values) + sum(
        _word_count(item.get("summary"))
        + sum(
            _word_count(x)
            for x in (
                item.get("study_focus")
                if isinstance(item.get("study_focus"), list)
                else []
            )
        )
        for item in guidance
        if isinstance(item, dict)
    )
    if total_editorial_words < 180:
        result.errors.append(
            f"editorial content must contain at least 180 substantive words (got {total_editorial_words})"
        )

    signals = overlay.get("study_signals")
    if signals is not None:
        if not isinstance(signals, dict):
            result.errors.append("study_signals must be an object")
        else:
            record_count = signals.get("input_record_count")
            if not isinstance(record_count, int) or record_count < 0:
                result.errors.append("study_signals.input_record_count must be a non-negative integer")
            if not SHA256_PATTERN.match(str(signals.get("input_dataset_hash") or "")):
                result.errors.append("study_signals.input_dataset_hash must be sha256:<64 hex chars>")
            if signals.get("derivation") != "aggregate_metadata_only":
                result.errors.append(
                    "study_signals.derivation must be aggregate_metadata_only"
                )
            if signals.get("official_weighting") is not False:
                result.errors.append("study_signals.official_weighting must be false")
            topics = signals.get("topic_emphasis")
            if not isinstance(topics, list):
                result.errors.append("study_signals.topic_emphasis must be an array")
                topics = []
            for index, item in enumerate(topics):
                if not isinstance(item, dict):
                    result.errors.append(f"study_signals.topic_emphasis[{index}] must be an object")
                    continue
                share = item.get("share_percent")
                if share is not None and (
                    not isinstance(share, (int, float)) or share < 0 or share > 100
                ):
                    result.errors.append(
                        f"study_signals.topic_emphasis[{index}].share_percent must be between 0 and 100"
                    )

    lifecycle = overlay.get("lifecycle")
    if lifecycle is not None:
        if not isinstance(lifecycle, dict):
            result.errors.append("lifecycle must be an object")
        else:
            status = lifecycle.get("status")
            if status not in {"retired", "scheduled_retirement"}:
                result.errors.append(
                    "lifecycle.status must be retired or scheduled_retirement"
                )
            else:
                date_field = (
                    "retires_on"
                    if status == "scheduled_retirement"
                    else "retired_on"
                )
                if not _valid_iso_date(lifecycle.get(date_field)):
                    result.errors.append(
                        f"lifecycle.{date_field} must be an ISO date"
                    )
            if _word_count(lifecycle.get("summary")) < 20:
                result.errors.append("lifecycle.summary must contain at least 20 words")

            replacement = lifecycle.get("replacement")
            has_replacement = replacement is not None
            if has_replacement:
                if not isinstance(replacement, dict):
                    result.errors.append("lifecycle.replacement must be an object")
                    replacement = {}
                for field_name in ("exam_code", "name"):
                    if not str(replacement.get(field_name) or "").strip():
                        result.errors.append(
                            f"lifecycle.replacement.{field_name} is required"
                        )
                for field_name in ("url", "study_guide_url"):
                    if not _is_https_url(replacement.get(field_name)):
                        result.errors.append(
                            f"lifecycle.replacement.{field_name} must be an https URL"
                        )
                relationship = replacement.get("relationship", "direct_replacement")
                if relationship not in {
                    "direct_replacement",
                    "collective_replacement",
                    "related_successor",
                }:
                    result.errors.append(
                        "lifecycle.replacement.relationship must be direct_replacement, "
                        "collective_replacement, or related_successor"
                    )

            actions = lifecycle.get("migration_actions")
            if not isinstance(actions, list) or len(
                [item for item in actions if str(item).strip()]
            ) < 2:
                result.errors.append(
                    "lifecycle.migration_actions must contain at least 2 items"
                )

            comparisons = lifecycle.get("skill_comparison")
            if has_replacement and (
                not isinstance(comparisons, list) or not comparisons
            ):
                result.errors.append(
                    "lifecycle.skill_comparison must contain at least one mapping when a replacement is named"
                )
                comparisons = []
            elif comparisons is None:
                comparisons = []
            elif not isinstance(comparisons, list):
                result.errors.append("lifecycle.skill_comparison must be an array")
                comparisons = []
            for index, item in enumerate(comparisons):
                prefix = f"lifecycle.skill_comparison[{index}]"
                if not isinstance(item, dict):
                    result.errors.append(f"{prefix} must be an object")
                    continue
                for field_name in (
                    "legacy_skill",
                    "legacy_weight",
                    "replacement_skill",
                    "replacement_weight",
                    "change",
                ):
                    if not str(item.get(field_name) or "").strip():
                        result.errors.append(f"{prefix}.{field_name} is required")

            refs = lifecycle.get("source_ids")
            if not isinstance(refs, list) or not refs:
                result.errors.append("lifecycle.source_ids is required")
            else:
                for source_id in refs:
                    if source_id not in source_ids:
                        result.errors.append(f"unknown source reference: {source_id}")

            methodology = editorial.get("methodology")
            if not isinstance(methodology, dict):
                result.errors.append(
                    "editorial.methodology is required for retired migration pages"
                )
            else:
                if _word_count(methodology.get("summary")) < 20:
                    result.errors.append(
                        "editorial.methodology.summary must contain at least 20 words"
                    )
                method_refs = methodology.get("source_ids")
                if not isinstance(method_refs, list) or not method_refs:
                    result.errors.append("editorial.methodology.source_ids is required")
                else:
                    for source_id in method_refs:
                        if source_id not in source_ids:
                            result.errors.append(
                                f"unknown source reference: {source_id}"
                            )

    return result


def merge_overlay(exam: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    """Return public exam data with an approved overlay, or unchanged data on failure."""
    validation = validate_overlay(exam, overlay)
    if not validation.publishable:
        return copy.deepcopy(exam)

    merged = copy.deepcopy(exam)
    merged["editorial"] = copy.deepcopy(overlay["editorial"])
    if "study_signals" in overlay:
        if isinstance(overlay.get("study_signals"), dict):
            merged["study_signals"] = copy.deepcopy(overlay["study_signals"])
        else:
            merged.pop("study_signals", None)
    if overlay.get("lifecycle"):
        merged["lifecycle"] = copy.deepcopy(overlay["lifecycle"])
    merged["sources"] = copy.deepcopy(overlay["sources"])
    merged["content_quality"] = copy.deepcopy(overlay["quality"])
    fact_overrides = overlay.get("fact_overrides")
    if isinstance(fact_overrides, dict):
        by_domain_id = {
            str(item.get("domain_id") or ""): item
            for item in fact_overrides.get("domains", [])
            if isinstance(item, dict)
        }
        for domain in merged.get("domains", []):
            if not isinstance(domain, dict):
                continue
            override = by_domain_id.get(str(domain.get("id") or ""))
            if not override:
                continue
            domain["weight_percent"] = None
            domain["weight_min_percent"] = override["weight_min_percent"]
            domain["weight_max_percent"] = override["weight_max_percent"]
            if override.get("corrected_name"):
                domain["name"] = override["corrected_name"]
        objective_overrides = {
            (str(item.get("domain_id") or ""), str(item.get("objective_id") or "")): item
            for item in fact_overrides.get("objectives", [])
            if isinstance(item, dict)
        }
        for domain in merged.get("domains", []):
            if not isinstance(domain, dict):
                continue
            domain_id = str(domain.get("id") or "")
            for objective in domain.get("objectives", []):
                if not isinstance(objective, dict):
                    continue
                override = objective_overrides.get(
                    (domain_id, str(objective.get("id") or ""))
                )
                if override:
                    objective["id"] = override["corrected_id"]
    return merged


def has_public_enrichment(exam: dict[str, Any]) -> bool:
    quality = exam.get("content_quality")
    return (
        isinstance(quality, dict)
        and quality.get("status") == "reviewed"
        and quality.get("publishable") is True
        and isinstance(exam.get("editorial"), dict)
    )


def load_and_merge_overlay(
    exam: dict[str, Any],
    vendor_slug: str,
    enrichment_root: Path | str,
) -> tuple[dict[str, Any], ValidationResult | None]:
    """Load a Git overlay for an exam and merge it only when it passes validation."""
    path = Path(enrichment_root) / vendor_slug / f"{exam.get('exam_id', '')}.json"
    if not path.exists():
        return copy.deepcopy(exam), None
    try:
        overlay = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return copy.deepcopy(exam), ValidationResult(errors=[f"invalid overlay {path}: {error}"])
    validation = validate_overlay(exam, overlay)
    return merge_overlay(exam, overlay), validation


def should_publish_exam(exam: dict[str, Any], existing_exam_ids: set[str]) -> bool:
    """Keep existing URLs stable; require approved enrichment for every new URL."""
    return str(exam.get("exam_id") or "") in existing_exam_ids or has_public_enrichment(exam)
