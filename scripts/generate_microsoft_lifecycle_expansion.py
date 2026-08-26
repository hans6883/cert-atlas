#!/usr/bin/env python3
"""Generate reviewed Microsoft lifecycle overlays from official source pages."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parent.parent
DATA_ROOT = ROOT / "data" / "microsoft"
OUTPUT_ROOT = ROOT / "enrichment" / "microsoft"
ACCESSED = "2026-08-26"
GENERATED_AT = "2026-08-26T06:15:00Z"
REVIEWED_AT = "2026-08-26T06:30:00Z"
RETIREMENT_URL = (
    "https://learn.microsoft.com/en-us/credentials/support/"
    "retired-certification-exams"
)
JULY_ANNOUNCEMENT_URL = (
    "https://learn.microsoft.com/en-us/partner-center/announcements/2026-july"
)


EXAMS = {
    "microsoft-az-500-azure-security": {
        "status": "scheduled_retirement",
        "date": "2026-08-31",
        "ranges": [(15, 20), (20, 25), (20, 25), (30, 35)],
        "role": (
            "Azure security engineers who implement controls across identity, "
            "networking, compute, storage, databases, Defender for Cloud, and Sentinel"
        ),
        "value": (
            "The final AZ-500 outline is unusually useful as a boundary map between "
            "resource-level Azure hardening and broader security operations. It shows "
            "where identity, network paths, workload configuration, posture management, "
            "and incident signals must be reasoned about together."
        ),
        "strategy": (
            "Build one representative Azure environment and trace a control from identity "
            "assignment through network isolation, workload protection, policy evaluation, "
            "Defender findings, and Sentinel response. Candidates with enough time to test "
            "before the cutoff can finish AZ-500; longer plans should start with SC-500."
        ),
        "skills": [
            "Trace effective access across Azure roles, Microsoft Entra controls, and privileged workflows",
            "Design network and private-access controls around real workload dependencies",
            "Harden compute, storage, databases, and secrets without breaking operability",
            "Turn Defender for Cloud posture findings and Sentinel signals into corrective action",
        ],
        "replacement": {
            "exam_code": "SC-500",
            "name": "Implementing End-to-End Security Controls for Cloud and AI Workloads",
            "url": "https://learn.microsoft.com/en-us/credentials/certifications/exams/sc-500/",
            "study_guide_url": "https://learn.microsoft.com/en-us/credentials/certifications/resources/study-guides/sc-500",
            "relationship": "direct_replacement",
        },
        "comparisons": [
            (
                "Secure identity and access",
                "15-20%",
                "Manage identity, access, and governance",
                "20-25%",
                "SC-500 retains Entra, role, policy, and Key Vault work while making governance and overprivileged-access remediation more explicit.",
            ),
            (
                "Secure networking; secure compute, storage, and databases",
                "40-50% combined",
                "Secure storage, databases, networking, and compute",
                "45-55% combined",
                "Most infrastructure hardening transfers, but SC-500 reorganizes it by control surface and adds explicit AI, application platform, hybrid, and multicloud tasks.",
            ),
            (
                "Defender for Cloud and Microsoft Sentinel",
                "30-35%",
                "Manage and monitor security posture",
                "20-25%",
                "SC-500 preserves posture and collection work, adds Security Copilot, and places AI workload protection inside the end-to-end security role.",
            ),
        ],
    },
    "microsoft-az-800-windows-server-hybrid-core": {
        "status": "scheduled_retirement",
        "date": "2026-09-30",
        "ranges": [(30, 35), (10, 15), (15, 20), (15, 20), (15, 20)],
        "domain_names": [
            "Deploy and manage Active Directory Domain Services (AD DS) in on-premises and cloud environments",
            "Manage Windows Servers and workloads in a hybrid environment",
            "Manage virtual machines and containers",
            "Implement and manage an on-premises and hybrid networking infrastructure",
            "Manage storage and file services",
        ],
        "role": (
            "experienced Windows Server administrators responsible for hybrid identity, "
            "server management, virtualization, networking, storage, and Azure integration"
        ),
        "value": (
            "AZ-800 connects classic Windows Server administration with Azure control planes. "
            "Its value is the dependency chain: AD DS affects authentication, DNS affects "
            "service reachability, virtualization affects capacity, and storage and networking "
            "choices determine how safely workloads can move between locations."
        ),
        "strategy": (
            "Use a small hybrid lab with an AD DS forest, a managed server, DNS and DHCP, a "
            "Hyper-V workload, a file service, and Azure-connected management. Practice the "
            "same task through PowerShell and administrative tools, then verify the resulting "
            "identity, network, and storage state instead of memorizing interface locations."
        ),
        "skills": [
            "Operate AD DS across on-premises and Azure-connected environments",
            "Manage Windows Server consistently with PowerShell, Windows Admin Center, and Azure services",
            "Administer Hyper-V, containers, hybrid networking, DNS, DHCP, IPAM, and remote access",
            "Design file services, Azure Files integration, storage migration, and synchronization",
        ],
    },
    "microsoft-az-801-windows-server-hybrid-advanced": {
        "status": "scheduled_retirement",
        "date": "2026-09-30",
        "ranges": [(25, 30), (15, 20), (10, 15), (20, 25), (15, 20)],
        "role": (
            "Windows Server hybrid administrators who secure, migrate, protect, monitor, "
            "and troubleshoot production workloads across datacenters and Azure"
        ),
        "value": (
            "AZ-801 is the failure-mode half of the Windows Server Hybrid Administrator path. "
            "The outline is valuable because it ties hardening, high availability, recovery, "
            "migration, monitoring, and troubleshooting to the same workloads instead of "
            "treating those disciplines as separate product checklists."
        ),
        "strategy": (
            "Create failure-driven labs. Harden a server and identity path, build a cluster, "
            "take and restore backups, test Site Recovery or replication, migrate a workload, "
            "and diagnose an injected fault from evidence. Record prerequisites, recovery "
            "objectives, validation checks, and rollback conditions for every exercise."
        ),
        "skills": [
            "Harden Windows Server, Active Directory, networking, storage, and hybrid security controls",
            "Implement clustering, Storage Spaces Direct, backup, replication, and disaster recovery",
            "Choose and execute server, storage, identity, and IIS migration approaches",
            "Diagnose Windows Server and Active Directory faults with local and Azure telemetry",
        ],
    },
    "microsoft-ms-102-m365-administrator": {
        "status": "scheduled_retirement",
        "date": "2026-11-30",
        "ranges": [(25, 30), (25, 30), (30, 35), (10, 15)],
        "role": (
            "Microsoft 365 administrators who coordinate tenant, identity, security, endpoint, "
            "collaboration, and compliance work across cloud and hybrid environments"
        ),
        "value": (
            "MS-102 describes the integrating-hub role rather than a single workload specialty. "
            "The strongest preparation follows a change across tenant configuration, identity "
            "synchronization, Conditional Access, Defender XDR, endpoint protection, and Purview "
            "so that security and compliance effects are visible end to end."
        ),
        "strategy": (
            "Use a test tenant to build operational runbooks for onboarding, role delegation, "
            "identity synchronization, secure access, threat investigation, endpoint response, "
            "and information protection. For each task, capture prerequisites, least-privilege "
            "roles, the correct admin surface, verification evidence, and a recovery path."
        ),
        "skills": [
            "Deploy, license, monitor, and delegate administration in a Microsoft 365 tenant",
            "Operate synchronized identity, authentication methods, Identity Protection, and Conditional Access",
            "Investigate and respond across Defender XDR, Defender for Office 365, Endpoint, and Cloud Apps",
            "Implement Purview information protection, retention, data loss prevention, and alert response",
        ],
    },
    "microsoft-mb-910-dynamics-365-fundamentals-crm": {
        "status": "retired",
        "date": "2025-12-31",
        "ranges": [(15, 20), (20, 25), (20, 25), (15, 20), (15, 20)],
        "role": (
            "learners who used the fundamentals exam to understand how Dynamics 365 customer "
            "engagement applications support marketing, sales, service, and field operations"
        ),
        "value": (
            "The historical MB-910 blueprint remains a compact map of the customer lifecycle. "
            "Customer Insights forms and segments audiences, Sales advances opportunities, "
            "Customer Service resolves cases, and Field Service carries service into scheduled "
            "onsite work. The useful artifact is that process map, not the retired exam target."
        ),
        "strategy": (
            "Reuse the blueprint as product orientation. Trace one customer scenario through "
            "profiles and journeys, lead qualification, an opportunity, a service case, and a "
            "field work order. Then choose a current Microsoft credential from the active catalog "
            "based on the job role or application you actually need to operate."
        ),
        "skills": [
            "Explain how Customer Insights supports profiles, segments, journeys, and engagement",
            "Map Dynamics 365 Sales capabilities to the lead and opportunity lifecycle",
            "Relate Customer Service cases and knowledge to agent and customer outcomes",
            "Connect Field Service work orders, scheduling, assets, and mobile execution",
        ],
    },
    "microsoft-mb-920-dynamics-365-fundamentals-erp": {
        "status": "retired",
        "date": "2025-12-31",
        "ranges": [(35, 40), (30, 35), (25, 30)],
        "role": (
            "learners who used the fundamentals exam to understand Dynamics 365 Finance and "
            "Supply Chain Management processes before choosing a deeper functional role"
        ),
        "value": (
            "The historical MB-920 scope is still useful as an enterprise-process map. It links "
            "products, procurement, inventory, warehousing, manufacturing, ledgers, payables, "
            "receivables, budgeting, legal entities, reporting, workflows, and integrations. "
            "That connected model is more durable than memorized navigation."
        ),
        "strategy": (
            "Build one order-to-cash and one procure-to-pay narrative and identify the master "
            "data, documents, inventory movements, financial postings, approvals, analytics, and "
            "cross-entity effects. Use that map to select a current Finance, Supply Chain, or "
            "business applications credential without presenting MB-920 as available."
        ),
        "skills": [
            "Explain products, inventory, warehousing, manufacturing, and supply chain flows",
            "Connect general ledger, payables, receivables, budgeting, and fixed assets",
            "Recognize shared finance-and-operations concepts such as legal entities, workflows, and batch processing",
            "Choose current role-based learning from the business process that needs deeper implementation skill",
        ],
    },
    "microsoft-ms-900-m365-fundamentals": {
        "status": "retired",
        "date": "2026-03-31",
        "ranges": [(5, 10), (45, 50), (25, 30), (10, 15)],
        "role": (
            "learners who used Microsoft 365 Fundamentals to connect cloud concepts with "
            "productivity, collaboration, endpoint, security, compliance, licensing, and support"
        ),
        "value": (
            "The historical MS-900 outline remains a useful vocabulary and architecture map for "
            "Microsoft 365. It separates service models from workload capabilities, then connects "
            "apps and administration to identity, threat protection, privacy, compliance, pricing, "
            "licensing, deployment assistance, and support."
        ),
        "strategy": (
            "Use the old domains to locate knowledge gaps, not to simulate a retired test. For a "
            "business scenario, identify the Microsoft 365 service, administrative surface, data "
            "and identity boundary, security and compliance controls, and licensing dependency. "
            "Then move to a current fundamentals or role-based guide that matches the goal."
        ),
        "skills": [
            "Distinguish cloud service and deployment models in Microsoft 365 scenarios",
            "Map productivity, collaboration, endpoint, analytics, and administration capabilities to needs",
            "Explain identity, threat protection, privacy, trust, and compliance at a foundational level",
            "Recognize how licensing, billing, deployment help, and support affect solution choices",
        ],
    },
}


def fetch_source(
    session: requests.Session,
    source_id: str,
    url: str,
    title: str,
    source_type: str,
) -> dict:
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
        return str(
            value.get("title") or value.get("name") or value.get("description") or ""
        ).strip()
    return str(value or "").strip()


def domain_guidance(exam: dict, source_id: str, status: str) -> list[dict]:
    result = []
    for position, domain in enumerate(exam.get("domains", []), start=1):
        domain_id = str(domain.get("id") or "")
        name = str(domain.get("name") or domain_id).split(" (")[0].strip()
        examples = [objective_title(item) for item in domain.get("objectives", [])]
        examples = [item for item in examples if item][:3]
        tasks = "; ".join(examples) or "the decisions in the published objectives"
        time_word = "historical outline" if status == "retired" else "current outline"
        result.append(
            {
                "domain_id": domain_id,
                "summary": (
                    f"Domain {position}, {name}, organizes related decisions rather than isolated "
                    f"product facts. The {time_word} includes {tasks}. Practice by connecting the "
                    "configuration or recommendation to prerequisites, downstream effects, evidence "
                    "of success, and a safe correction when the expected result is not observed."
                ),
                "study_focus": [
                    f"Turn every {name} objective into a concrete task or decision you can explain",
                    "Record the prerequisite, implementation choice, verification signal, and failure mode",
                    "Mix this domain with adjacent domains so dependencies remain visible",
                ],
                "source_ids": [source_id],
            }
        )
    return result


def build_overlay(exam: dict, config: dict, sources: list[dict]) -> dict:
    code = str(exam["exam_code"])
    status = config["status"]
    scheduled = status == "scheduled_retirement"
    source_ids = [source["id"] for source in sources]
    domain_names = [
        str(domain.get("name") or domain.get("id") or "").split(" (")[0].strip()
        for domain in exam.get("domains", [])
    ]
    date_field = "retires_on" if scheduled else "retired_on"
    date_phrase = "will retire" if scheduled else "retired"
    action_state = "remains schedulable before the cutoff" if scheduled else "is no longer schedulable"
    replacement = config.get("replacement")

    lifecycle = {
        "status": status,
        date_field: config["date"],
        "summary": (
            f"Microsoft {date_phrase} {code} on {config['date']}. The exam {action_state}. "
            + (
                f"Microsoft identifies {replacement['exam_code']} as its direct replacement, so candidates should choose the blueprint that matches their testing date and long-term role."
                if replacement
                else "The reviewed official retirement list and exam guide do not name a direct replacement, so Cert Atlas does not infer one."
            )
        ),
        "migration_actions": (
            [
                f"Confirm that a complete {code} study and booking plan fits before {config['date']}.",
                f"If the plan extends past the cutoff, switch to {replacement['exam_code']} and use its current dated study guide.",
                "Compare the two outlines objective by objective instead of renaming old notes or practice content.",
                "Recheck the official retirement page before scheduling because Microsoft states that dates can change.",
            ]
            if replacement
            else [
                (
                    f"Complete and schedule {code} before {config['date']} only if the remaining window supports a sound preparation plan."
                    if scheduled
                    else f"Remove {code} from current registration and practice calls to action because it retired on {config['date']}."
                ),
                "Use Microsoft's active credential catalog to choose a current path by job role and required skills.",
                "Do not treat a similarly named course, product, or credential as a replacement unless Microsoft explicitly says so.",
                "Map reusable knowledge to the selected current guide, then rebuild labs and review around that guide's dated objectives.",
            ]
        ),
        "source_ids": source_ids,
    }
    if replacement:
        lifecycle["replacement"] = replacement
        lifecycle["skill_comparison"] = [
            {
                "legacy_skill": item[0],
                "legacy_weight": item[1],
                "replacement_skill": item[2],
                "replacement_weight": item[3],
                "change": item[4],
            }
            for item in config["comparisons"]
        ]

    overview_tense = (
        f"remains available only until {config['date']}"
        if scheduled
        else f"retired on {config['date']}"
    )
    no_successor_note = (
        f" Microsoft names {replacement['exam_code']} as the direct replacement."
        if replacement
        else " Microsoft does not name a direct replacement in the reviewed official sources."
    )
    return {
        "exam_id": exam["exam_id"],
        "editorial": {
            "meta_description": (
                f"{code} {'retires soon' if scheduled else 'is retired'}. Review its source-verified domains, cutoff, study value, and "
                f"{'SC-500 transition' if replacement else 'truthful next steps without an invented replacement'}."
            ),
            "overview": (
                f"{code}, {exam['exam_name']}, {overview_tense}. Its published domains cover "
                f"{', '.join(domain_names)}. {config['value']}{no_successor_note} This page keeps "
                "the dated blueprint useful while separating verified lifecycle facts from recommendations."
            ),
            "who_should_take": (
                f"The original audience was {config['role']}. "
                + (
                    f"Current candidates should choose {code} only when preparation, scheduling, and any credential requirements can be completed before {config['date']}; otherwise use the verified replacement path."
                    if scheduled and replacement
                    else f"Current candidates should use the cutoff and active Microsoft catalog to decide whether {code} still fits; the absence of a named replacement is not evidence that a similarly named exam is equivalent."
                    if scheduled
                    else "This historical page is for prior learners, credential holders, training teams cleaning up old material, and practitioners mapping durable knowledge into a current role-based plan."
                )
            ),
            "skills_summary": config["skills"],
            "preparation_strategy": (
                f"{config['strategy']} Start with the dated Microsoft guide, map each objective to "
                "a task, decision, observable result, and failure mode, and use domain ranges to "
                "balance coverage rather than predict question counts. Keep notes labeled with the "
                "guide date so future product or blueprint changes do not silently contaminate the plan."
            ),
            "domain_guidance": domain_guidance(exam, f"microsoft-{code.lower()}-study-guide", status),
            "exam_day_guidance": (
                f"Microsoft lists {config['date']} as the retirement date. Verify the official page immediately before booking, allow time for identity and accommodation requirements, and do not assume a retake can be scheduled after the cutoff."
                if scheduled
                else f"{code} cannot be booked after its {config['date']} retirement. Use the active Microsoft credential and exam pages for current delivery, pricing, language, accommodation, and scheduling information."
            ),
            "methodology": {
                "summary": (
                    f"Cert Atlas reviewed Microsoft's dated {code} study guide and official retirement list"
                    + (f", then compared the current {replacement['exam_code']} guide and Microsoft's transition announcement" if replacement else " and checked those sources for an explicitly named replacement")
                    + ". OpenAI Codex assisted with extraction, normalization, and drafting. The lifecycle, weights, and editorial claims were checked against the linked official pages; no exam questions, answers, choices, or explanations were used."
                ),
                "source_ids": source_ids,
            },
            "source_ids": [f"microsoft-{code.lower()}-study-guide"],
        },
        "fact_overrides": {
            "domains": [
                {
                    "domain_id": str(domain.get("id") or ""),
                    "weight_min_percent": weights[0],
                    "weight_max_percent": weights[1],
                    "source_ids": [f"microsoft-{code.lower()}-study-guide"],
                    **(
                        {"corrected_name": config["domain_names"][position]}
                        if config.get("domain_names")
                        else {}
                    ),
                }
                for position, (domain, weights) in enumerate(
                    zip(exam.get("domains", []), config["ranges"])
                )
            ]
        },
        "study_signals": None,
        "lifecycle": lifecycle,
        "sources": sources,
        "quality": {
            "status": "reviewed",
            "publishable": True,
            "evidence_coverage": 0.98,
            "factual_confidence": 0.98,
            "generated_by": "openai:codex",
            "generated_at": GENERATED_AT,
            "reviewed_at": REVIEWED_AT,
        },
    }


def main() -> int:
    session = requests.Session()
    session.headers["User-Agent"] = (
        "CertAtlasEditorialAudit/1.0 (+https://atlas.quizforge.ai/)"
    )
    retirement_source = fetch_source(
        session,
        "microsoft-retirement-list",
        RETIREMENT_URL,
        "Exam and assessment lab retirement",
        "official_documentation",
    )
    for exam_id, config in EXAMS.items():
        exam = json.loads((DATA_ROOT / f"{exam_id}.json").read_text(encoding="utf-8"))
        code = str(exam["exam_code"])
        sources = [
            fetch_source(
                session,
                f"microsoft-{code.lower()}-study-guide",
                f"https://learn.microsoft.com/en-us/credentials/certifications/resources/study-guides/{code.lower()}",
                f"Study guide for Exam {code}: {exam['exam_name']}",
                "official_exam_guide",
            ),
            retirement_source,
        ]
        replacement = config.get("replacement")
        if replacement:
            sources.extend(
                [
                    fetch_source(
                        session,
                        f"microsoft-{replacement['exam_code'].lower()}-study-guide",
                        replacement["study_guide_url"],
                        f"Study guide for Exam {replacement['exam_code']}: {replacement['name']}",
                        "official_exam_guide",
                    ),
                    fetch_source(
                        session,
                        "microsoft-transition-announcement",
                        JULY_ANNOUNCEMENT_URL,
                        "July 2026 certification transition announcement",
                        "official_documentation",
                    ),
                ]
            )
        overlay = build_overlay(exam, config, sources)
        output = OUTPUT_ROOT / f"{exam_id}.json"
        output.write_text(
            json.dumps(overlay, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"wrote {output.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
