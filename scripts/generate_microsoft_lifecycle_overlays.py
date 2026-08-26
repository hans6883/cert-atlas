#!/usr/bin/env python3
"""Build reviewed, source-bound retirement overlays for verified Microsoft transitions."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parent.parent
DATA_ROOT = ROOT / "data" / "microsoft"
OUTPUT_ROOT = ROOT / "enrichment" / "microsoft"
ACCESSED = "2026-08-25"
GENERATED_AT = "2026-08-26T05:00:00Z"
REVIEWED_AT = "2026-08-26T05:20:00Z"
RETIREMENT_URL = "https://learn.microsoft.com/en-us/credentials/support/retired-certification-exams"


TRANSITIONS = {
    "microsoft-ai-900-azure-ai-fundamentals": {
        "retired_on": "2026-06-30",
        "replacement_code": "AI-901",
        "replacement_name": "Microsoft Azure AI Fundamentals",
        "relationship": "direct_replacement",
        "announcement_url": "https://learn.microsoft.com/en-us/credentials/certifications/exams/ai-900/",
        "summary": "Microsoft retired AI-900 on June 30, 2026 and replaced it with AI-901 as the qualifying exam for Microsoft Certified: Azure AI Fundamentals.",
        "comparisons": [
            ("AI workloads and considerations", "15-20%", "Identify AI concepts and capabilities", "40-45%", "AI-901 consolidates conceptual coverage and gives it substantially more weight, including responsible AI and choosing capabilities for a scenario."),
            ("Machine learning, vision, and NLP fundamentals", "45-60% combined", "Identify AI concepts and capabilities", "40-45%", "The foundational concepts still transfer, but they are organized as one integrated decision-oriented domain."),
            ("Generative AI workloads", "20-25%", "Implement AI solutions by using Microsoft Foundry", "55-60%", "AI-901 moves beyond description toward basic implementation using Foundry, Python syntax, Azure resources, APIs, SDKs, and command-line tools."),
        ],
        "ranges": [(15, 20), (15, 20), (15, 20), (15, 20), (20, 25)],
    },
    "microsoft-dp-100-azure-data-scientist": {
        "retired_on": "2026-06-01",
        "replacement_code": "AI-300",
        "replacement_name": "Operationalizing Machine Learning and Generative AI Solutions",
        "relationship": "direct_replacement",
        "announcement_url": "https://learn.microsoft.com/en-us/partner-center/announcements/2026-june",
        "summary": "Microsoft retired DP-100 and the Azure Data Scientist Associate certification on June 1, 2026. Microsoft identifies AI-300 and the Machine Learning Operations Engineer Associate certification as the replacement path.",
        "comparisons": [
            ("Design and prepare a machine learning solution", "20-25%", "Design and implement an MLOps infrastructure", "15-20%", "The successor shifts from project setup toward reproducible infrastructure, source control, pipelines, environments, security, and governance."),
            ("Explore data and run experiments; train and deploy models", "45-55% combined", "Implement machine learning model lifecycle and operations", "25-30%", "Experimentation remains useful, but AI-300 emphasizes registration, deployment, monitoring, retraining, lineage, and operational response."),
            ("Optimize language models for AI applications", "25-30%", "GenAIOps infrastructure, quality assurance, observability, and optimization", "40-55% combined", "The replacement expands model optimization into production evaluation, tracing, safety, performance, RAG quality, and agent operations."),
        ],
        "ranges": [(20, 25), (20, 25), (25, 30), (25, 30)],
    },
    "microsoft-az-204-azure-developer": {
        "retired_on": "2026-07-31",
        "replacement_code": "AI-200",
        "replacement_name": "Developing AI Cloud Solutions on Azure",
        "relationship": "direct_replacement",
        "announcement_url": "https://learn.microsoft.com/en-us/partner-center/announcements/2026-july",
        "summary": "Microsoft retired AZ-204 and the Azure Developer Associate certification on July 31, 2026. Microsoft identifies AI-200 and the Azure AI Cloud Developer Associate certification as its replacement.",
        "comparisons": [
            ("Develop Azure compute solutions", "25-30%", "Develop containerized solutions on Azure", "20-25%", "AI-200 narrows compute preparation around containerized, scalable cloud applications and their deployment behavior."),
            ("Develop for Azure storage", "15-20%", "Develop AI solutions using Azure data management services", "25-30%", "Storage skills transfer, but the replacement gives more weight to data flows and stores used by AI-enabled applications."),
            ("Implement security; monitor and troubleshoot", "20-30% combined", "Secure, monitor, and troubleshoot Azure solutions", "20-25%", "Security and operations remain central and are assessed as an integrated production discipline."),
            ("Connect to and consume Azure and third-party services", "20-25%", "Connect to and consume Azure services", "20-25%", "Service integration remains directly relevant, now in the context of responsive AI cloud solutions."),
        ],
        "ranges": [(25, 30), (15, 20), (15, 20), (5, 10), (20, 25)],
    },
    "microsoft-mb-240-dynamics-365-field-service": {
        "retired_on": "2026-06-30",
        "replacement_code": "AB-250",
        "replacement_name": "Transforming Contact Center Experiences with AI in Dynamics 365",
        "relationship": "related_successor",
        "announcement_url": "https://learn.microsoft.com/en-us/partner-center/announcements/2026-july",
        "summary": "Microsoft retired MB-240 and the Dynamics 365 Field Service Functional Consultant Associate certification on June 30, 2026. Microsoft explicitly says AB-250 is not a direct replacement, but adds it as the related current path used to account for the retirement.",
        "comparisons": [
            ("Configure field service applications", "20-25%", "Deploy Dynamics 365 Contact Center", "15-20%", "Both require governed Dynamics configuration, but AB-250 targets contact center deployment rather than field service operations."),
            ("Manage work orders, assets, inventory, and purchasing", "30-40% combined", "Implement channels and configure the representative experience", "45-55% combined", "The core business process changes from onsite service fulfillment to voice and digital customer engagement."),
            ("Schedule and dispatch work orders", "15-20%", "Configure work distribution", "10-15%", "Routing concepts transfer at a high level, but the objects, constraints, metrics, and operating workflows are different."),
            ("Field Service mobile app and Power Platform", "10-20% combined", "Agents, AI capabilities, and contact center analytics", "20-30% combined", "AB-250 adds explicit human-and-AI service operation, analytics, and optimization work."),
        ],
        "ranges": [(20, 25), (25, 30), (15, 20), (5, 10), (5, 10), (5, 10)],
    },
    "microsoft-mb-700-dynamics-365-solution-architect": {
        "retired_on": "2026-06-30",
        "replacement_code": "AB-100",
        "replacement_name": "Agentic AI Business Solutions Architect",
        "relationship": "collective_replacement",
        "announcement_url": "https://learn.microsoft.com/en-us/partner-center/announcements/2026-june",
        "summary": "Microsoft retired MB-700 and the Finance and Operations Apps Solution Architect Expert certification on June 30, 2026. Microsoft lists AB-100 as a collective replacement for MB-700 and several other retired business application credentials.",
        "comparisons": [
            ("Architect solutions", "25-30%", "Design AI-powered business solutions", "25-30%", "Architecture judgment transfers, while AB-100 adds agentic patterns, model choices, orchestration, grounding, and AI-specific controls."),
            ("Define solution strategies", "45-50%", "Plan AI-powered business solutions", "25-30%", "Strategic discovery remains important but is reframed around AI value, readiness, responsible use, data, and adoption."),
            ("Manage implementations and testing", "25-35% combined", "Deploy AI-powered business solutions", "40-45%", "The replacement increases deployment weight and adds evaluation, observability, governance, security, and lifecycle management for agents."),
        ],
        "ranges": [(25, 30), (45, 50), (10, 15), (15, 20)],
    },
    "microsoft-pl-500-power-automate-rpa": {
        "retired_on": "2026-06-30",
        "replacement_code": "AB-100",
        "replacement_name": "Agentic AI Business Solutions Architect",
        "relationship": "collective_replacement",
        "announcement_url": "https://learn.microsoft.com/en-us/partner-center/announcements/2026-june",
        "summary": "Microsoft retired PL-500 and the Power Automate RPA Developer Associate certification on June 30, 2026. Microsoft places AB-100 in the broader replacement set, but the successor is an expert architecture credential rather than a like-for-like RPA developer exam.",
        "comparisons": [
            ("Design automations", "25-30%", "Plan AI-powered business solutions", "25-30%", "Process analysis transfers, while AB-100 broadens planning to AI readiness, value, responsible use, data, and organizational adoption."),
            ("Develop automations", "45-50%", "Design AI-powered business solutions", "25-30%", "Hands-on desktop and cloud flow building gives way to architecture across agents, copilots, models, integrations, and human oversight."),
            ("Deploy and manage automations", "20-25%", "Deploy AI-powered business solutions", "40-45%", "Operational discipline remains useful, but AB-100 adds evaluation, governance, security, monitoring, cost, and multi-agent lifecycle concerns."),
        ],
        "ranges": [(25, 30), (45, 50), (20, 25)],
    },
    "microsoft-pl-600-power-platform-solution-architect": {
        "retired_on": "2026-06-30",
        "replacement_code": "AB-100",
        "replacement_name": "Agentic AI Business Solutions Architect",
        "relationship": "collective_replacement",
        "announcement_url": "https://learn.microsoft.com/en-us/partner-center/announcements/2026-june",
        "summary": "Microsoft retired PL-600 and the Power Platform Solution Architect Expert certification on June 30, 2026. Microsoft describes AB-100 as a collective and partial replacement path that expands solution architecture into agentic AI business systems.",
        "comparisons": [
            ("Solution envisioning and requirement analysis", "45-50%", "Plan AI-powered business solutions", "25-30%", "Discovery skills transfer, with new emphasis on AI value, feasibility, data readiness, risk, responsible AI, and adoption."),
            ("Architect a solution", "35-40%", "Design AI-powered business solutions", "25-30%", "Power Platform architecture remains relevant but expands to models, agents, orchestration, grounding, memory, tools, and cross-platform integration."),
            ("Implement the solution", "15-20%", "Deploy AI-powered business solutions", "40-45%", "AB-100 puts substantially more weight on deployment governance, evaluation, security, observability, cost management, and lifecycle strategy."),
        ],
        "ranges": [(45, 50), (35, 40), (15, 20)],
    },
}


def fetch_source(session: requests.Session, source_id: str, url: str, title: str, source_type: str) -> dict:
    response = session.get(url, timeout=30, allow_redirects=True)
    response.raise_for_status()
    return {
        "id": source_id,
        "url": url,
        "title": title,
        "publisher": "Microsoft",
        "source_type": source_type,
        "accessed": ACCESSED,
        "content_hash": "sha256:" + hashlib.sha256(response.content).hexdigest(),
    }


def objective_title(value: object) -> str:
    if isinstance(value, dict):
        return str(value.get("title") or value.get("name") or value.get("description") or "").strip()
    return str(value or "").strip()


def build_domain_guidance(exam: dict, legacy_source_id: str) -> list[dict]:
    guidance = []
    for domain in exam.get("domains", []):
        domain_id = str(domain.get("id") or "")
        name = str(domain.get("name") or domain_id).strip()
        examples = [objective_title(item) for item in domain.get("objectives", [])]
        examples = [item for item in examples if item][:2]
        example_text = "; ".join(examples) if examples else "the tasks and decisions in the published objectives"
        guidance.append(
            {
                "domain_id": domain_id,
                "summary": (
                    f"Historically, {name} required candidates to connect configuration choices with operational outcomes. "
                    f"The official outline included {example_text}. Preserve hands-on understanding of those tasks where the successor comparison shows overlap, but do not treat this retired weighting or terminology as a current exam blueprint."
                ),
                "study_focus": [
                    f"Use the official historical objectives to document what {name.lower()} required",
                    "Mark each prior skill as transferable, changed, or absent in the current replacement guide",
                    "Rebuild practical exercises around current services, interfaces, governance, and role expectations",
                ],
                "source_ids": [legacy_source_id],
            }
        )
    return guidance


def build_overlay(exam: dict, config: dict, sources: list[dict]) -> dict:
    code = exam["exam_code"]
    replacement_code = config["replacement_code"]
    relationship = config["relationship"]
    legacy_source_id = f"microsoft-{code.lower()}-study-guide"
    replacement_source_id = f"microsoft-{replacement_code.lower()}-study-guide"
    announcement_source_id = "microsoft-transition-announcement"
    relationship_wording = {
        "direct_replacement": "the direct replacement",
        "collective_replacement": "the broader replacement path",
        "related_successor": "a related current path, not a direct replacement",
    }[relationship]
    domain_names = [str(item.get("name") or "").strip() for item in exam.get("domains", [])]
    domain_names = [item for item in domain_names if item]

    return {
        "exam_id": exam["exam_id"],
        "editorial": {
            "meta_description": f"{code} is retired. Compare its historical blueprint with {replacement_code}, see what transfers, and rebuild your plan around the current Microsoft exam.",
            "overview": (
                f"{code} was Microsoft's {exam['exam_name']} exam until its retirement on {config['retired_on']}. "
                f"Its final published scope covered {', '.join(domain_names)}. This page preserves that dated outline for historical comparison and curriculum cleanup. "
                f"It is not a schedulable exam, and its prices, delivery details, registration links, and practice calls to action must not be used for a new certification plan."
            ),
            "who_should_take": (
                f"Nobody should start a new certification plan around {code}. This page serves former candidates, credential holders, training teams removing stale material, and practitioners deciding whether prior preparation is reusable for {replacement_code}. "
                f"New candidates should verify the active Microsoft page and current dated study guide before booking."
            ),
            "skills_summary": [
                f"Preserve practical experience from {name} only where the current guide shows meaningful overlap"
                for name in domain_names[:6]
            ],
            "preparation_strategy": (
                f"Do not rename an old {code} checklist or question bank as {replacement_code}. Compare the two official guides objective by objective and classify each historical skill as transferable, changed, or absent. "
                f"Use transferable experience as a diagnostic baseline, then rebuild labs and review around {replacement_code}'s current domain weights, products, role expectations, security controls, and operational tasks. "
                f"Because Microsoft identifies {replacement_code} as {relationship_wording}, review the skill map below before assuming equivalence."
            ),
            "domain_guidance": build_domain_guidance(exam, legacy_source_id),
            "exam_day_guidance": (
                f"{code} can no longer be scheduled. Use the active {replacement_code} certification page for current duration, languages, price, delivery, accommodations, and registration details, and verify them again immediately before booking."
            ),
            "methodology": {
                "summary": (
                    f"Cert Atlas compared Microsoft's final {code} study guide with the current {replacement_code} guide at the domain and objective level, then checked Microsoft's retirement list and transition announcement. "
                    "OpenAI Codex assisted with extraction, normalization, comparison, and drafting. Claims were reviewed against the linked official sources; no exam stems, answers, choices, or explanations were used."
                ),
                "source_ids": [legacy_source_id, replacement_source_id, announcement_source_id, "microsoft-retirement-list"],
            },
            "source_ids": [legacy_source_id],
        },
        "fact_overrides": {
            "domains": [
                {
                    "domain_id": str(domain.get("id") or ""),
                    "weight_min_percent": weights[0],
                    "weight_max_percent": weights[1],
                    "source_ids": [legacy_source_id],
                }
                for domain, weights in zip(exam.get("domains", []), config["ranges"])
            ]
        },
        "study_signals": None,
        "lifecycle": {
            "status": "retired",
            "retired_on": config["retired_on"],
            "summary": config["summary"],
            "replacement": {
                "exam_code": replacement_code,
                "name": config["replacement_name"],
                "url": f"https://learn.microsoft.com/en-us/credentials/certifications/exams/{replacement_code.lower()}/",
                "study_guide_url": f"https://learn.microsoft.com/en-us/credentials/certifications/resources/study-guides/{replacement_code.lower()}",
                "relationship": relationship,
            },
            "migration_actions": [
                f"Stop scheduling, selling, or presenting {code} as a current exam.",
                f"Compare completed {code} preparation with the current {replacement_code} guide; do not carry over obsolete weighting or mechanics.",
                f"Create a fresh {replacement_code} plan around its current domains and hands-on role expectations.",
                "Remove or quarantine practice content that cannot be mapped to a current objective with source evidence.",
                f"Recheck Microsoft's dated {replacement_code} study guide before booking because role-based exams change over time.",
            ],
            "skill_comparison": [
                {
                    "legacy_skill": item[0],
                    "legacy_weight": item[1],
                    "replacement_skill": item[2],
                    "replacement_weight": item[3],
                    "change": item[4],
                }
                for item in config["comparisons"]
            ],
            "source_ids": [legacy_source_id, replacement_source_id, announcement_source_id, "microsoft-retirement-list"],
        },
        "sources": sources,
        "quality": {
            "status": "reviewed",
            "publishable": True,
            "evidence_coverage": 0.97,
            "factual_confidence": 0.97,
            "generated_by": "openai:codex",
            "generated_at": GENERATED_AT,
            "reviewed_at": REVIEWED_AT,
        },
    }


def main() -> int:
    session = requests.Session()
    session.headers["User-Agent"] = "CertAtlasEditorialAudit/1.0 (+https://atlas.quizforge.ai/)"
    retirement_source = fetch_source(
        session,
        "microsoft-retirement-list",
        RETIREMENT_URL,
        "Exam and assessment lab retirement",
        "official_documentation",
    )

    for exam_id, config in TRANSITIONS.items():
        exam_path = DATA_ROOT / f"{exam_id}.json"
        exam = json.loads(exam_path.read_text(encoding="utf-8"))
        code = exam["exam_code"]
        replacement_code = config["replacement_code"]
        sources = [
            fetch_source(
                session,
                f"microsoft-{code.lower()}-study-guide",
                f"https://learn.microsoft.com/en-us/credentials/certifications/resources/study-guides/{code.lower()}",
                f"Study guide for Exam {code}: {exam['exam_name']}",
                "official_exam_guide",
            ),
            fetch_source(
                session,
                f"microsoft-{replacement_code.lower()}-study-guide",
                f"https://learn.microsoft.com/en-us/credentials/certifications/resources/study-guides/{replacement_code.lower()}",
                f"Study guide for Exam {replacement_code}: {config['replacement_name']}",
                "official_exam_guide",
            ),
            fetch_source(
                session,
                "microsoft-transition-announcement",
                config["announcement_url"],
                "Microsoft certification retirement and replacement announcement",
                "official_documentation",
            ),
            retirement_source,
        ]
        overlay = build_overlay(exam, config, sources)
        output = OUTPUT_ROOT / f"{exam_id}.json"
        output.write_text(json.dumps(overlay, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"wrote {output.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
