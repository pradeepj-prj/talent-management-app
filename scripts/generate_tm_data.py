#!/usr/bin/env python3
"""Generate realistic Talent Management (TM) skill data.

Reads active employees from the HR database (public schema) and generates
skill profiles, evidence, and org references in the TM schema (tm.*).

Usage:
    python scripts/generate_tm_data.py [--seed 42] [--sample-pct 70]
"""

import argparse
import random
import sys
from datetime import date, timedelta
from typing import Any

import psycopg2
from psycopg2.extras import execute_values

# ─── Configuration ────────────────────────────────────────────────────────────

DB_CONFIG = dict(
    host="13.228.165.215",
    port=5432,
    database="hr_data",
    user="hr_app",
    password="EPprjTjHCHBAgINSrJJ38LLS",
)

TODAY = date.today()

# ─── Skill Catalog ────────────────────────────────────────────────────────────
# Each skill: (name, category, description, [applicable_job_groups])
# Categories: technical, functional, leadership, domain, tool, other

SKILL_CATALOG: list[dict[str, Any]] = [
    # ── Software Engineering ──────────────────────────────────────────────────
    {"name": "Python", "category": "technical", "groups": ["software"],
     "desc": "Python programming for backend services, automation, and data processing"},
    {"name": "Java", "category": "technical", "groups": ["software"],
     "desc": "Java development for enterprise applications and microservices"},
    {"name": "Go", "category": "technical", "groups": ["software"],
     "desc": "Go programming for high-performance systems and cloud-native services"},
    {"name": "JavaScript", "category": "technical", "groups": ["software"],
     "desc": "JavaScript/ES6+ for frontend and Node.js backend development"},
    {"name": "TypeScript", "category": "technical", "groups": ["software"],
     "desc": "TypeScript for type-safe frontend and backend development"},
    {"name": "SQL", "category": "technical", "groups": ["software", "finance", "hr"],
     "desc": "SQL for relational database querying, optimization, and data analysis"},
    {"name": "REST API Design", "category": "technical", "groups": ["software"],
     "desc": "Designing RESTful APIs with proper versioning, pagination, and error handling"},
    {"name": "Microservices Architecture", "category": "technical", "groups": ["software"],
     "desc": "Designing and building distributed microservices systems"},
    {"name": "Cloud Architecture", "category": "technical", "groups": ["software"],
     "desc": "Designing scalable cloud-native architectures on AWS/GCP/Azure"},
    {"name": "System Design", "category": "technical", "groups": ["software"],
     "desc": "Large-scale system design including scalability, reliability, and performance"},
    {"name": "CI/CD", "category": "technical", "groups": ["software", "it"],
     "desc": "Continuous integration and deployment pipelines (Jenkins, GitHub Actions, GitLab CI)"},
    {"name": "Test Automation", "category": "technical", "groups": ["software"],
     "desc": "Automated testing frameworks (pytest, JUnit, Selenium, Cypress)"},
    {"name": "Docker", "category": "tool", "groups": ["software", "it"],
     "desc": "Container creation, management, and Docker Compose orchestration"},
    {"name": "Kubernetes", "category": "tool", "groups": ["software", "it"],
     "desc": "Container orchestration, deployment strategies, and cluster management"},
    {"name": "AWS", "category": "tool", "groups": ["software", "it"],
     "desc": "Amazon Web Services — EC2, S3, Lambda, RDS, CloudFormation"},
    {"name": "Git", "category": "tool", "groups": ["software"],
     "desc": "Version control with Git (branching strategies, rebasing, code review workflows)"},
    {"name": "PostgreSQL", "category": "tool", "groups": ["software"],
     "desc": "PostgreSQL database administration, query optimization, and extensions"},
    {"name": "Redis", "category": "tool", "groups": ["software"],
     "desc": "Redis for caching, session management, and pub/sub messaging"},
    {"name": "Terraform", "category": "tool", "groups": ["software", "it"],
     "desc": "Infrastructure as Code using Terraform for cloud resource provisioning"},

    # ── Hardware Engineering ──────────────────────────────────────────────────
    {"name": "PCB Design", "category": "technical", "groups": ["hardware"],
     "desc": "Multi-layer PCB layout, routing, and design for manufacturing"},
    {"name": "Signal Integrity Analysis", "category": "technical", "groups": ["hardware"],
     "desc": "High-speed signal integrity simulation and validation"},
    {"name": "Firmware Development", "category": "technical", "groups": ["hardware"],
     "desc": "Embedded firmware development in C/C++ for microcontrollers and SoCs"},
    {"name": "FPGA Design", "category": "technical", "groups": ["hardware"],
     "desc": "FPGA design using VHDL/Verilog for digital logic implementation"},
    {"name": "Analog Circuit Design", "category": "technical", "groups": ["hardware"],
     "desc": "Analog and mixed-signal circuit design (op-amps, ADCs, power supplies)"},
    {"name": "EMC/EMI Testing", "category": "technical", "groups": ["hardware"],
     "desc": "Electromagnetic compatibility testing and compliance (FCC, CE)"},
    {"name": "MATLAB", "category": "tool", "groups": ["hardware", "manufacturing"],
     "desc": "MATLAB for simulation, data analysis, and algorithm development"},
    {"name": "Simulink", "category": "tool", "groups": ["hardware"],
     "desc": "Simulink for model-based design and hardware-in-the-loop simulation"},
    {"name": "Altium Designer", "category": "tool", "groups": ["hardware"],
     "desc": "Altium Designer for schematic capture and PCB layout"},
    {"name": "Cadence OrCAD", "category": "tool", "groups": ["hardware"],
     "desc": "Cadence OrCAD for PCB design and signal integrity analysis"},

    # ── Manufacturing Engineering ─────────────────────────────────────────────
    {"name": "Lean Manufacturing", "category": "technical", "groups": ["manufacturing"],
     "desc": "Lean principles (5S, Kaizen, value stream mapping) for waste reduction"},
    {"name": "Six Sigma", "category": "technical", "groups": ["manufacturing", "quality"],
     "desc": "Six Sigma DMAIC methodology for process improvement and variation reduction"},
    {"name": "Statistical Process Control", "category": "technical", "groups": ["manufacturing", "quality"],
     "desc": "SPC charts, control limits, and process capability analysis (Cp, Cpk)"},
    {"name": "FMEA", "category": "technical", "groups": ["manufacturing", "quality"],
     "desc": "Failure Mode and Effects Analysis for risk identification and mitigation"},
    {"name": "Process Optimization", "category": "technical", "groups": ["manufacturing"],
     "desc": "Manufacturing process optimization for yield, throughput, and cost"},
    {"name": "Production Planning", "category": "functional", "groups": ["manufacturing"],
     "desc": "Production scheduling, capacity planning, and MRP"},
    {"name": "Supply Chain Management", "category": "functional", "groups": ["manufacturing"],
     "desc": "End-to-end supply chain planning, sourcing, and logistics"},
    {"name": "SolidWorks", "category": "tool", "groups": ["manufacturing", "hardware"],
     "desc": "3D CAD modeling, assemblies, and drawings using SolidWorks"},
    {"name": "SAP PP", "category": "tool", "groups": ["manufacturing"],
     "desc": "SAP Production Planning module for manufacturing execution"},
    {"name": "AutoCAD", "category": "tool", "groups": ["manufacturing"],
     "desc": "2D/3D drafting and design using AutoCAD"},

    # ── Quality Engineering ───────────────────────────────────────────────────
    {"name": "Root Cause Analysis", "category": "technical", "groups": ["quality"],
     "desc": "Systematic problem solving (5 Whys, Ishikawa, fault tree analysis)"},
    {"name": "Reliability Engineering", "category": "technical", "groups": ["quality"],
     "desc": "Reliability analysis, MTBF/MTTR, and accelerated life testing"},
    {"name": "Quality Auditing", "category": "technical", "groups": ["quality"],
     "desc": "Internal and supplier quality audits against ISO/IATF standards"},
    {"name": "Design of Experiments", "category": "technical", "groups": ["quality"],
     "desc": "DOE for optimizing product and process parameters"},
    {"name": "CAPA", "category": "domain", "groups": ["quality"],
     "desc": "Corrective and Preventive Action processes for quality management"},
    {"name": "Minitab", "category": "tool", "groups": ["quality", "manufacturing"],
     "desc": "Statistical analysis software for quality and process improvement"},
    {"name": "ISO 9001", "category": "domain", "groups": ["quality"],
     "desc": "ISO 9001 Quality Management System requirements and implementation"},
    {"name": "IATF 16949", "category": "domain", "groups": ["quality"],
     "desc": "Automotive quality management system standard"},

    # ── Sales ─────────────────────────────────────────────────────────────────
    {"name": "Consultative Selling", "category": "functional", "groups": ["sales"],
     "desc": "Needs-based selling approach focused on customer business outcomes"},
    {"name": "Pipeline Management", "category": "functional", "groups": ["sales"],
     "desc": "Sales pipeline tracking, forecasting, and stage management"},
    {"name": "Contract Negotiation", "category": "functional", "groups": ["sales"],
     "desc": "B2B contract negotiation, pricing strategies, and deal structuring"},
    {"name": "Account Management", "category": "functional", "groups": ["sales"],
     "desc": "Strategic account planning, relationship management, and expansion"},
    {"name": "Solution Selling", "category": "functional", "groups": ["sales"],
     "desc": "Solution-based selling methodology for complex enterprise deals"},
    {"name": "Sales Forecasting", "category": "functional", "groups": ["sales"],
     "desc": "Revenue forecasting using pipeline analysis and historical trends"},
    {"name": "Salesforce CRM", "category": "tool", "groups": ["sales"],
     "desc": "Salesforce administration, reporting, and pipeline management"},
    {"name": "HubSpot", "category": "tool", "groups": ["sales"],
     "desc": "HubSpot CRM and marketing automation platform"},
    {"name": "LinkedIn Sales Navigator", "category": "tool", "groups": ["sales"],
     "desc": "LinkedIn Sales Navigator for prospecting and social selling"},

    # ── HR ────────────────────────────────────────────────────────────────────
    {"name": "Talent Acquisition", "category": "functional", "groups": ["hr"],
     "desc": "End-to-end recruitment: sourcing, screening, interviewing, and onboarding"},
    {"name": "Employee Relations", "category": "functional", "groups": ["hr"],
     "desc": "Employee relations, conflict resolution, and disciplinary processes"},
    {"name": "Performance Management", "category": "functional", "groups": ["hr"],
     "desc": "Performance review cycles, goal setting, and calibration"},
    {"name": "Learning & Development", "category": "functional", "groups": ["hr"],
     "desc": "Training program design, LMS administration, and learning analytics"},
    {"name": "Workforce Planning", "category": "functional", "groups": ["hr"],
     "desc": "Strategic workforce planning, headcount modeling, and succession planning"},
    {"name": "HR Analytics", "category": "functional", "groups": ["hr"],
     "desc": "People analytics: attrition modeling, engagement surveys, workforce metrics"},
    {"name": "SuccessFactors", "category": "tool", "groups": ["hr"],
     "desc": "SAP SuccessFactors HCM suite (EC, RCM, PM, LMS modules)"},
    {"name": "Workday", "category": "tool", "groups": ["hr"],
     "desc": "Workday HCM for HR operations, payroll, and talent management"},

    # ── Finance ───────────────────────────────────────────────────────────────
    {"name": "Financial Analysis", "category": "functional", "groups": ["finance"],
     "desc": "Financial statement analysis, ratio analysis, and valuation"},
    {"name": "Budgeting & Forecasting", "category": "functional", "groups": ["finance"],
     "desc": "Annual budgeting, rolling forecasts, and variance analysis"},
    {"name": "Financial Reporting", "category": "functional", "groups": ["finance"],
     "desc": "GAAP/IFRS financial reporting, consolidation, and close process"},
    {"name": "Risk Management", "category": "functional", "groups": ["finance"],
     "desc": "Financial risk assessment, hedging strategies, and internal controls"},
    {"name": "Cost Accounting", "category": "functional", "groups": ["finance"],
     "desc": "Cost allocation, product costing, and activity-based costing"},
    {"name": "SAP FICO", "category": "tool", "groups": ["finance"],
     "desc": "SAP Financial Accounting and Controlling modules"},
    {"name": "Excel Financial Modeling", "category": "tool", "groups": ["finance"],
     "desc": "Advanced Excel for financial models, DCF, and scenario analysis"},
    {"name": "Tableau", "category": "tool", "groups": ["finance", "hr"],
     "desc": "Tableau for data visualization and business intelligence dashboards"},

    # ── IT ────────────────────────────────────────────────────────────────────
    {"name": "ITSM", "category": "functional", "groups": ["it"],
     "desc": "IT Service Management frameworks and incident/change management"},
    {"name": "Network Administration", "category": "technical", "groups": ["it"],
     "desc": "Network design, routing/switching, firewall configuration, and VPN"},
    {"name": "Cybersecurity", "category": "technical", "groups": ["it"],
     "desc": "Security operations, vulnerability management, and incident response"},
    {"name": "Cloud Infrastructure", "category": "technical", "groups": ["it"],
     "desc": "Cloud infrastructure management (AWS/Azure/GCP) and migration"},
    {"name": "Database Administration", "category": "technical", "groups": ["it"],
     "desc": "Database administration, backup/recovery, and performance tuning"},
    {"name": "ServiceNow", "category": "tool", "groups": ["it"],
     "desc": "ServiceNow ITSM platform for incident, problem, and change management"},
    {"name": "Active Directory", "category": "tool", "groups": ["it"],
     "desc": "Active Directory administration, Group Policy, and identity management"},
    {"name": "ITIL", "category": "domain", "groups": ["it"],
     "desc": "ITIL framework for IT service management best practices"},

    # ── Leadership (seniority 3+) ─────────────────────────────────────────────
    {"name": "People Management", "category": "leadership", "groups": ["leadership"],
     "desc": "Direct team management: hiring, coaching, performance reviews, career development"},
    {"name": "Strategic Planning", "category": "leadership", "groups": ["leadership"],
     "desc": "Long-term strategic planning, OKR setting, and roadmap development"},
    {"name": "Coaching & Mentoring", "category": "leadership", "groups": ["leadership"],
     "desc": "Coaching direct reports and mentoring emerging leaders"},
    {"name": "Stakeholder Management", "category": "leadership", "groups": ["leadership"],
     "desc": "Managing executive stakeholders, cross-functional alignment, and influence"},
    {"name": "Change Management", "category": "leadership", "groups": ["leadership"],
     "desc": "Leading organizational change initiatives and transformation programs"},
    {"name": "Executive Communication", "category": "leadership", "groups": ["leadership"],
     "desc": "Executive-level presentations, board communication, and strategic messaging"},
    {"name": "Project Management", "category": "leadership", "groups": ["leadership"],
     "desc": "Project planning, risk management, and delivery (Agile/Waterfall)"},
    {"name": "Team Building", "category": "leadership", "groups": ["leadership"],
     "desc": "Building high-performing teams, fostering collaboration, and team culture"},

    # ── Cross-cutting (all job groups) ────────────────────────────────────────
    {"name": "Communication", "category": "functional", "groups": ["cross"],
     "desc": "Written and verbal communication across technical and non-technical audiences"},
    {"name": "Problem Solving", "category": "functional", "groups": ["cross"],
     "desc": "Analytical and creative problem-solving approaches"},
    {"name": "Critical Thinking", "category": "functional", "groups": ["cross"],
     "desc": "Structured thinking, data-driven decision making, and logical analysis"},
    {"name": "Presentation Skills", "category": "functional", "groups": ["cross"],
     "desc": "Creating and delivering effective presentations to diverse audiences"},
    {"name": "Data Analysis", "category": "functional", "groups": ["cross"],
     "desc": "Data analysis, interpretation, and insight generation"},
]

# ─── Job Group Mapping ────────────────────────────────────────────────────────
# Maps job_id prefix to a group key used for skill selection

JOB_ID_TO_GROUP = {
    "JR001": "software", "JR002": "software", "JR003": "software",
    "JR004": "software", "JR005": "software", "JR006": "software", "JR007": "software",
    "JR010": "hardware", "JR011": "hardware", "JR012": "hardware",
    "JR013": "hardware", "JR014": "hardware", "JR015": "hardware",
    "JR020": "manufacturing", "JR021": "manufacturing", "JR022": "manufacturing",
    "JR023": "manufacturing", "JR024": "manufacturing",
    "JR030": "quality", "JR031": "quality", "JR032": "quality",
    "JR033": "quality", "JR034": "quality",
    "JR100": "sales", "JR101": "sales", "JR102": "sales",
    "JR103": "sales", "JR104": "sales", "JR105": "sales",
    "JR200": "hr", "JR201": "hr", "JR202": "hr",
    "JR210": "finance", "JR211": "finance", "JR212": "finance", "JR213": "finance",
    "JR220": "it", "JR221": "it", "JR222": "it",
}

# ─── Evidence Templates ───────────────────────────────────────────────────────

CERT_TEMPLATES: dict[str, list[tuple[str, str]]] = {
    # (title, issuer)
    "software": [
        ("AWS Solutions Architect Associate", "Amazon Web Services"),
        ("AWS Solutions Architect Professional", "Amazon Web Services"),
        ("Certified Kubernetes Administrator (CKA)", "CNCF"),
        ("Google Cloud Professional Cloud Architect", "Google Cloud"),
        ("HashiCorp Terraform Associate", "HashiCorp"),
        ("Python for Data Science Specialization", "Coursera"),
        ("MongoDB Certified Developer", "MongoDB"),
        ("Confluent Kafka Developer", "Confluent"),
    ],
    "hardware": [
        ("IPC-A-610 Certification", "IPC"),
        ("Certified LabVIEW Associate Developer", "National Instruments"),
        ("Altium Designer Certified Professional", "Altium"),
        ("PCB Design with Altium", "Udemy"),
    ],
    "manufacturing": [
        ("Lean Six Sigma Green Belt", "ASQ"),
        ("Lean Six Sigma Black Belt", "ASQ"),
        ("APICS CPIM", "ASCM"),
        ("SAP PP Certification", "SAP"),
    ],
    "quality": [
        ("ASQ Certified Quality Engineer (CQE)", "ASQ"),
        ("ISO 9001 Lead Auditor", "BSI"),
        ("IATF 16949 Internal Auditor", "TUV"),
        ("Certified Reliability Engineer (CRE)", "ASQ"),
    ],
    "sales": [
        ("Salesforce Certified Administrator", "Salesforce"),
        ("HubSpot Inbound Sales Certification", "HubSpot"),
        ("Strategic Selling Certification", "Miller Heiman"),
        ("Challenger Sales Methodology", "CEB"),
    ],
    "hr": [
        ("SHRM-CP", "SHRM"),
        ("SuccessFactors Employee Central", "SAP"),
        ("Workday HCM Certification", "Workday"),
        ("People Analytics Specialization", "Coursera"),
    ],
    "finance": [
        ("CFA Level I", "CFA Institute"),
        ("SAP FICO Certification", "SAP"),
        ("Financial Modeling & Valuation Analyst", "CFI"),
        ("Advanced Excel for Finance", "LinkedIn Learning"),
    ],
    "it": [
        ("ITIL Foundation v4", "Axelos"),
        ("CompTIA Security+", "CompTIA"),
        ("AWS Cloud Practitioner", "Amazon Web Services"),
        ("Cisco CCNA", "Cisco"),
        ("ServiceNow System Administrator", "ServiceNow"),
    ],
    "leadership": [
        ("PMP", "PMI"),
        ("Certified Scrum Master (CSM)", "Scrum Alliance"),
        ("Leadership Excellence Program", "Coursera"),
        ("Executive Leadership Certificate", "Harvard Business School Online"),
    ],
}

PROJECT_TEMPLATES = [
    "Led {} implementation for Q{quarter} {year}",
    "Architected {} solution for cross-functional team",
    "Delivered {} optimization reducing cost by {pct}%",
    "Migrated legacy system to {} stack",
    "Built {} prototype for new product line",
    "Designed {} framework adopted by {n} teams",
    "Spearheaded {} initiative across APJ region",
    "Implemented {} best practices for department",
]

ASSESSMENT_PLATFORMS = [
    ("HackerRank", "HackerRank"),
    ("Pluralsight IQ", "Pluralsight"),
    ("Internal Skills Assessment", "Internal"),
    ("LinkedIn Skill Assessment", "LinkedIn"),
    ("Codility Assessment", "Codility"),
]

SOURCE_WEIGHTS = {
    "self": 35,
    "manager": 20,
    "assessment": 15,
    "certification": 12,
    "peer": 10,
    "inferred": 5,
    "system": 3,
}

CONFIDENCE_RANGES = {
    "certification": (80, 95),
    "assessment": (70, 90),
    "manager": (60, 85),
    "system": (55, 75),
    "peer": (50, 75),
    "self": (40, 70),
    "inferred": (30, 50),
}


# ─── Helper Functions ─────────────────────────────────────────────────────────

def build_group_skill_index() -> dict[str, list[dict]]:
    """Build a mapping from job_group → list of applicable skills."""
    index: dict[str, list[dict]] = {}
    for skill in SKILL_CATALOG:
        for group in skill["groups"]:
            index.setdefault(group, []).append(skill)
    return index


def pick_skills_for_employee(
    job_group: str,
    seniority: int,
    group_index: dict[str, list[dict]],
    rng: random.Random,
) -> list[dict]:
    """Select skills for an employee based on their job group and seniority."""
    # Base skill count: 4-8 for junior, 8-14 for mid, 12-20 for senior
    base_min = 3 + seniority
    base_max = 6 + seniority * 3
    num_skills = rng.randint(base_min, min(base_max, 20))

    selected: list[dict] = []

    # 1. Primary skills from job group (60-70% of total)
    primary_skills = group_index.get(job_group, [])
    num_primary = min(len(primary_skills), int(num_skills * 0.65))
    selected.extend(rng.sample(primary_skills, num_primary))

    # 2. Leadership skills for seniority >= 3
    if seniority >= 3:
        leadership_skills = group_index.get("leadership", [])
        # More leadership skills for higher seniority
        num_leadership = min(len(leadership_skills), rng.randint(1, seniority - 1))
        selected.extend(rng.sample(leadership_skills, num_leadership))

    # 3. Cross-cutting skills (1-3)
    cross_skills = group_index.get("cross", [])
    num_cross = rng.randint(1, min(3, len(cross_skills)))
    selected.extend(rng.sample(cross_skills, num_cross))

    # 4. Fill remaining from adjacent groups (skill adjacency)
    remaining = num_skills - len(selected)
    if remaining > 0:
        adjacent_groups = _get_adjacent_groups(job_group)
        adjacent_pool = []
        for ag in adjacent_groups:
            adjacent_pool.extend(group_index.get(ag, []))
        # Remove already-selected skills
        selected_names = {s["name"] for s in selected}
        adjacent_pool = [s for s in adjacent_pool if s["name"] not in selected_names]
        if adjacent_pool:
            num_adjacent = min(remaining, len(adjacent_pool))
            selected.extend(rng.sample(adjacent_pool, num_adjacent))

    # De-duplicate by skill name (in case of overlap across groups)
    seen = set()
    unique = []
    for s in selected:
        if s["name"] not in seen:
            seen.add(s["name"])
            unique.append(s)
    return unique


def _get_adjacent_groups(job_group: str) -> list[str]:
    """Return adjacent job groups for skill bleed-over."""
    adjacency = {
        "software": ["it", "hardware"],
        "hardware": ["software", "manufacturing"],
        "manufacturing": ["quality", "hardware"],
        "quality": ["manufacturing"],
        "sales": ["hr", "finance"],
        "hr": ["sales", "finance"],
        "finance": ["hr", "it"],
        "it": ["software", "finance"],
    }
    return adjacency.get(job_group, [])


def generate_proficiency(seniority: int, is_primary: bool, rng: random.Random) -> int:
    """Generate a proficiency score (0-5) correlated with seniority."""
    if is_primary:
        # Primary skills: strongly correlated with seniority
        base = max(1, seniority - 1)  # seniority 1→0..3, 5→2..5
        return min(5, rng.randint(base, min(base + 2, 5)))
    else:
        # Adjacent/cross skills: lower proficiency
        return rng.randint(1, min(seniority + 1, 4))


def generate_source(rng: random.Random) -> str:
    """Pick a skill source weighted by realistic distribution."""
    sources = list(SOURCE_WEIGHTS.keys())
    weights = list(SOURCE_WEIGHTS.values())
    return rng.choices(sources, weights=weights, k=1)[0]


def generate_confidence(source: str, evidence_count: int, days_since_update: int, rng: random.Random) -> int:
    """Calculate confidence score based on source, evidence, and recency."""
    lo, hi = CONFIDENCE_RANGES[source]
    base = rng.randint(lo, hi)

    # Bonus for evidence
    base += min(evidence_count * 5, 25)

    # Penalty for staleness
    if days_since_update > 365:
        base -= 20
    elif days_since_update > 180:
        base -= 10

    return max(0, min(100, base))


def generate_last_updated(is_stale: bool, rng: random.Random) -> date:
    """Generate a last_updated_at date. Stale = older than 1 year."""
    if is_stale:
        days_ago = rng.randint(366, 1095)  # 1-3 years ago
    else:
        days_ago = rng.randint(1, 270)  # within ~9 months
    return TODAY - timedelta(days=days_ago)


def generate_evidence_items(
    skill_name: str,
    job_group: str,
    proficiency: int,
    source: str,
    last_updated: date,
    rng: random.Random,
) -> list[dict]:
    """Generate 0-5 evidence items for a skill. More evidence for higher proficiency."""
    # Higher proficiency → more evidence
    max_evidence = min(proficiency, 5)
    if max_evidence <= 0:
        return []
    num_evidence = rng.randint(0, max_evidence)
    if num_evidence == 0:
        return []

    items = []
    for _ in range(num_evidence):
        etype, item = _make_evidence_item(skill_name, job_group, source, last_updated, rng)
        items.append(item)
    return items


def _make_evidence_item(
    skill_name: str,
    job_group: str,
    source: str,
    last_updated: date,
    rng: random.Random,
) -> tuple[str, dict]:
    """Create a single evidence item."""
    # Pick evidence type correlated with source
    etype = _source_to_evidence_type(source, rng)

    # Generate evidence date near last_updated_at (±90 days before)
    offset = rng.randint(0, 90)
    evidence_date = last_updated - timedelta(days=offset)

    signal_strength = rng.randint(2, 5)

    if etype == "certification":
        certs = CERT_TEMPLATES.get(job_group, CERT_TEMPLATES.get("software", []))
        if certs:
            title, issuer = rng.choice(certs)
        else:
            title, issuer = f"{skill_name} Certification", "Various"
        return etype, {
            "evidence_type": etype,
            "title": title,
            "issuer_or_system": issuer,
            "evidence_date": evidence_date,
            "url_or_ref": f"https://certificates.example.com/verify/{rng.randint(10000, 99999)}",
            "signal_strength": max(signal_strength, 3),  # certs are strong signals
            "notes": None,
        }

    elif etype == "project":
        template = rng.choice(PROJECT_TEMPLATES)
        title = template.format(
            skill_name,
            quarter=rng.randint(1, 4),
            year=evidence_date.year,
            pct=rng.randint(10, 40),
            n=rng.randint(3, 12),
        )
        return etype, {
            "evidence_type": etype,
            "title": title,
            "issuer_or_system": "Internal",
            "evidence_date": evidence_date,
            "url_or_ref": f"PROJ-{rng.randint(1000, 9999)}",
            "signal_strength": signal_strength,
            "notes": None,
        }

    elif etype == "assessment":
        platform, issuer = rng.choice(ASSESSMENT_PLATFORMS)
        score = rng.randint(60, 100)
        return etype, {
            "evidence_type": etype,
            "title": f"{platform}: {skill_name} — Score {score}/100",
            "issuer_or_system": issuer,
            "evidence_date": evidence_date,
            "url_or_ref": None,
            "signal_strength": signal_strength,
            "notes": f"Percentile: top {rng.randint(5, 40)}%",
        }

    elif etype == "manager_validation":
        q = (evidence_date.month - 1) // 3 + 1
        return etype, {
            "evidence_type": etype,
            "title": f"Q{q} {evidence_date.year} Performance Review — {skill_name} proficiency validated",
            "issuer_or_system": "Manager",
            "evidence_date": evidence_date,
            "url_or_ref": None,
            "signal_strength": signal_strength,
            "notes": None,
        }

    elif etype == "peer_endorsement":
        return etype, {
            "evidence_type": etype,
            "title": f"Peer endorsement for {skill_name} expertise",
            "issuer_or_system": "Peer",
            "evidence_date": evidence_date,
            "url_or_ref": None,
            "signal_strength": max(2, signal_strength - 1),
            "notes": None,
        }

    else:  # work_history, portfolio, other
        return "work_history", {
            "evidence_type": "work_history",
            "title": f"Applied {skill_name} in role responsibilities",
            "issuer_or_system": "System",
            "evidence_date": evidence_date,
            "url_or_ref": None,
            "signal_strength": rng.randint(1, 3),
            "notes": None,
        }


def _source_to_evidence_type(source: str, rng: random.Random) -> str:
    """Map source to a likely evidence type."""
    mapping = {
        "certification": ["certification"],
        "assessment": ["assessment"],
        "manager": ["manager_validation", "project"],
        "peer": ["peer_endorsement"],
        "self": ["project", "portfolio", "work_history"],
        "inferred": ["work_history"],
        "system": ["assessment", "work_history"],
    }
    candidates = mapping.get(source, ["work_history"])
    return rng.choice(candidates)


# ─── Main Generation Logic ────────────────────────────────────────────────────

def run(seed: int = 42, sample_pct: int = 70):
    rng = random.Random(seed)
    group_index = build_group_skill_index()

    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False
    cur = conn.cursor()

    try:
        print("═" * 60)
        print("  Talent Management Data Generator")
        print("═" * 60)

        # ── Step 0: Clean existing TM data ────────────────────────
        print("\n[1/6] Cleaning existing TM data...")
        cur.execute("TRUNCATE tm.skill_evidence, tm.employee_skill, tm.employee_ref, tm.skill, tm.org_unit_ref CASCADE")
        conn.commit()

        # ── Step 1: Populate org_unit_ref ─────────────────────────
        print("[2/6] Syncing org units from HR...")
        cur.execute("SELECT org_id, org_name, parent_org_id, business_unit FROM organization_unit ORDER BY org_id")
        org_rows = cur.fetchall()

        # Insert parent orgs first (parent_org_id IS NULL), then children
        # Simple approach: insert all with deferred FK check
        cur.execute("SET CONSTRAINTS ALL DEFERRED")
        execute_values(
            cur,
            "INSERT INTO tm.org_unit_ref (org_id, org_name, parent_org_id, business_unit) VALUES %s",
            org_rows,
        )
        conn.commit()
        print(f"   → {len(org_rows)} org units synced")

        # ── Step 2: Read active employees from HR ─────────────────
        print("[3/6] Reading active employees from HR...")
        cur.execute("""
            SELECT e.employee_id, e.first_name, e.last_name,
                   ja.job_id, ja.job_title, ja.job_family, ja.seniority_level,
                   oa.org_id, oa.org_name
            FROM employee e
            JOIN employee_job_assignment ja ON e.employee_id = ja.employee_id AND ja.end_date IS NULL
            JOIN employee_org_assignment oa ON e.employee_id = oa.employee_id AND oa.end_date IS NULL
            WHERE e.employment_status = 'Active'
            ORDER BY e.employee_id
        """)
        all_employees = cur.fetchall()
        print(f"   → {len(all_employees)} active employees found")

        # Sample the configured percentage
        sample_size = max(1, int(len(all_employees) * sample_pct / 100))
        selected_employees = rng.sample(all_employees, sample_size)
        selected_employees.sort(key=lambda r: r[0])  # sort by employee_id
        print(f"   → {len(selected_employees)} employees selected ({sample_pct}% sample)")

        # ── Step 3: Insert skill catalog ──────────────────────────
        print("[4/6] Inserting skill catalog...")
        skill_values = [
            (s["name"], s["category"], s["desc"])
            for s in SKILL_CATALOG
        ]
        execute_values(
            cur,
            "INSERT INTO tm.skill (name, category, description) VALUES %s",
            skill_values,
        )
        conn.commit()

        # Retrieve skill_id mapping
        cur.execute("SELECT skill_id, name FROM tm.skill")
        skill_id_map = {name: sid for sid, name in cur.fetchall()}
        print(f"   → {len(skill_id_map)} skills inserted")

        # ── Step 4: Generate employee skill profiles ──────────────
        print("[5/6] Generating employee skill profiles...")
        employee_ref_rows = []
        employee_skill_rows = []
        evidence_rows = []

        stale_threshold = 0.17  # ~17% of skills will be stale
        stats = {"total_skills": 0, "total_evidence": 0, "stale_count": 0}

        for emp in selected_employees:
            emp_id, first, last, job_id, job_title, job_family, seniority, org_id, org_name = emp
            job_group = JOB_ID_TO_GROUP.get(job_id, "software")

            # employee_ref row
            display_name = f"{first} {last}"
            work_email = f"{first.lower()}.{last.lower()}@globalcorp.com"
            employee_ref_rows.append((
                emp_id, display_name, work_email,
                job_title, job_family, org_id, org_name, seniority, "active",
            ))

            # Pick skills for this employee
            skills = pick_skills_for_employee(job_group, seniority, group_index, rng)

            for skill in skills:
                skill_id = skill_id_map[skill["name"]]
                is_primary = job_group in skill["groups"]
                is_stale = rng.random() < stale_threshold

                proficiency = generate_proficiency(seniority, is_primary, rng)
                source = generate_source(rng)
                last_updated = generate_last_updated(is_stale, rng)
                days_since = (TODAY - last_updated).days

                # Generate evidence before confidence (evidence count affects confidence)
                evidence_items = generate_evidence_items(
                    skill["name"], job_group, proficiency, source, last_updated, rng
                )
                confidence = generate_confidence(source, len(evidence_items), days_since, rng)

                employee_skill_rows.append((
                    emp_id, skill_id, proficiency, confidence, source, last_updated,
                ))

                for ev in evidence_items:
                    evidence_rows.append((
                        emp_id, skill_id, ev["evidence_type"], ev["title"],
                        ev["issuer_or_system"], ev["evidence_date"],
                        ev["url_or_ref"], ev["signal_strength"], ev["notes"],
                    ))

                stats["total_skills"] += 1
                stats["total_evidence"] += len(evidence_items)
                if is_stale:
                    stats["stale_count"] += 1

        # ── Step 5: Bulk insert all data ──────────────────────────
        print("[6/6] Writing to database...")

        # employee_ref
        execute_values(
            cur,
            """INSERT INTO tm.employee_ref
               (employee_id, display_name, work_email, job_title, job_family,
                org_id, org_name, seniority_level, status)
               VALUES %s""",
            employee_ref_rows,
        )

        # employee_skill (with explicit last_updated_at to support stale injection)
        execute_values(
            cur,
            """INSERT INTO tm.employee_skill
               (employee_id, skill_id, proficiency, confidence, source, last_updated_at)
               VALUES %s""",
            employee_skill_rows,
        )

        # skill_evidence
        if evidence_rows:
            execute_values(
                cur,
                """INSERT INTO tm.skill_evidence
                   (employee_id, skill_id, evidence_type, title, issuer_or_system,
                    evidence_date, url_or_ref, signal_strength, notes)
                   VALUES %s""",
                evidence_rows,
            )

        conn.commit()

        # ── Summary ───────────────────────────────────────────────
        print("\n" + "═" * 60)
        print("  Generation Complete!")
        print("═" * 60)
        print(f"  Employees profiled:  {len(selected_employees):,}")
        print(f"  Skills in catalog:   {len(skill_id_map):,}")
        print(f"  Skill assignments:   {stats['total_skills']:,}")
        print(f"  Evidence items:      {stats['total_evidence']:,}")
        print(f"  Stale skills:        {stats['stale_count']:,} ({100*stats['stale_count']/max(1,stats['total_skills']):.1f}%)")
        print(f"  Avg skills/employee: {stats['total_skills']/len(selected_employees):.1f}")
        print(f"  Avg evidence/skill:  {stats['total_evidence']/max(1,stats['total_skills']):.1f}")
        print("═" * 60)

    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate TM skill data from HR employee base")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility (default: 42)")
    parser.add_argument("--sample-pct", type=int, default=70, help="Percentage of active employees to profile (default: 70)")
    args = parser.parse_args()

    run(seed=args.seed, sample_pct=args.sample_pct)
