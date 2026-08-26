#!/usr/bin/env python3
"""Build a provider-neutral structured-output request for an enrichment model."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from scripts.enrichment import is_prohibited_bank_key
except ImportError:
    from enrichment import is_prohibited_bank_key


def _prohibited_paths(value: Any, path: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            if is_prohibited_bank_key(key):
                found.append(child_path)
            found.extend(_prohibited_paths(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_prohibited_paths(child, f"{path}[{index}]"))
    return found


def build_generation_request(
    evidence_pack: dict[str, Any],
    study_signals: dict[str, Any] | None,
    *,
    system_prompt: str,
    schema: dict[str, Any],
) -> dict[str, Any]:
    unsafe = _prohibited_paths(evidence_pack.get("exam", {}))
    unsafe.extend(_prohibited_paths(study_signals or {}))
    if unsafe:
        raise ValueError("prohibited bank-shaped input fields: " + ", ".join(unsafe))

    payload = {
        "evidence_pack": evidence_pack,
        "study_signals": study_signals,
        "instructions": {
            "output": "one JSON object matching the supplied schema",
            "writer_cannot_self_approve": True,
            "official_sources_control_factual_claims": True,
        },
    }
    return {
        "messages": [
            {"role": "system", "content": system_prompt.strip()},
            {
                "role": "user",
                "content": json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            },
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "cert_atlas_enrichment",
                "strict": True,
                "schema": schema,
            },
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-pack", required=True, type=Path)
    parser.add_argument("--study-signals", type=Path)
    parser.add_argument("--system-prompt", default=Path("prompts/editorial-system.md"), type=Path)
    parser.add_argument("--schema", default=Path("schema/enrichment.schema.json"), type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    evidence = json.loads(args.evidence_pack.read_text(encoding="utf-8"))
    signals = (
        json.loads(args.study_signals.read_text(encoding="utf-8"))
        if args.study_signals
        else None
    )
    prompt = args.system_prompt.read_text(encoding="utf-8")
    schema = json.loads(args.schema.read_text(encoding="utf-8"))
    request = build_generation_request(evidence, signals, system_prompt=prompt, schema=schema)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(request, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote structured generation request: {args.output}")


if __name__ == "__main__":
    main()
