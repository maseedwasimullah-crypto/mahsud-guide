"""Seed content that has been VERIFIED against an official document.

Every entry records the exact source URL and the date it was retrieved, so any
developer can re-check it. Nothing here is invented: if a value was not visible
in an official source it is left out and the gap is reported in the research
report instead.

Retrieval date for everything below: 2026-10-19.
"""

from __future__ import annotations

from datetime import date

from .constants import DocType, FormulaStatus, RuleType, Verification

RETRIEVED_ON = date(2026, 10, 19)

# --------------------------------------------------------------------------- #
# Official source registry
# --------------------------------------------------------------------------- #
SOURCES: list[dict] = [
    {
        "name": "Khyber Medical University — official website",
        "url": "https://kmu.edu.pk/",
        "institution": "Khyber Medical University, Peshawar",
        "category": "university",
        "is_official": True,
        "verification_status": Verification.VERIFIED,
        "verification_notes": "Official KMU domain; homepage and primary navigation verified on 2026-10-19.",
    },
    {
        "name": "KMU — Admissions",
        "url": "https://kmu.edu.pk/admissions",
        "institution": "Khyber Medical University, Peshawar",
        "category": "admissions",
        "is_official": True,
        "verification_status": Verification.VERIFIED,
        "verification_notes": "Lists the official admission portals for MBBS, BS, KMU-ISB and postgraduate admissions.",
    },
    {
        "name": "KMU Centralized Admission System — MBBS/BDS public sector colleges of KP",
        "url": "https://cas.kmu.edu.pk/",
        "institution": "Khyber Medical University, Peshawar",
        "category": "admissions",
        "is_official": True,
        "verification_status": Verification.VERIFIED,
        "verification_notes": "Linked from kmu.edu.pk/admissions as the 2025-26 MBBS admission portal.",
    },
    {
        "name": "KMU Admission Policy (Public Sector Medical & Dental Colleges of KP) 2025-26",
        "url": "https://cas.kmu.edu.pk/sitedocuments/Admission-Policy-Public-2025-26.pdf",
        "institution": "Government of Khyber Pakhtunkhwa / KMU / PM&DC",
        "category": "policy",
        "is_official": True,
        "verification_status": Verification.VERIFIED,
        "verification_notes": (
            "Primary admission policy document. Confirms the merit weightage (SSC 10%, FSc 40%, "
            "MDCAT 50%), the eligibility thresholds (60% HSSC, 55% MDCAT MBBS / 50% BDS) and a "
            "worked aggregate example. Downloaded and parsed on 2026-10-19."
        ),
    },
    {
        "name": "KMU BS Undergraduate (Allied Health) Centralized Admission Portal — Peshawar Region",
        "url": "https://bsadmissions.kmu.edu.pk/",
        "institution": "Khyber Medical University, Peshawar",
        "category": "admissions",
        "is_official": True,
        "verification_status": Verification.VERIFIED,
        "verification_notes": (
            "Session 2026-27. States eligibility (FSc Pre-Medical >= 50% for BS, >= 60% for DPT, "
            "KMU-CAT 2026 mandatory), merit weightage (SSC 10%, HSSC 50%, entrance 40%), the "
            "admission schedule (forms 20-06-2026 to 09-10-2026) and the quota list."
        ),
    },
    {
        "name": "KMU Faculty of Nursing — BS Nursing Centralized Admission Portal",
        "url": "https://nursing.kmu.edu.pk/",
        "institution": "Khyber Medical University, Peshawar",
        "category": "admissions",
        "is_official": True,
        "verification_status": Verification.VERIFIED,
        "verification_notes": (
            "Session 2026-27. Eligibility (FSc Pre-Medical >= 50%, age 17-35, KMU-CAT 2026), "
            "merit weightage (SSC 10%, HSSC 50%, entrance 40%), schedule (21-06-2026 to 09-10-2026)."
        ),
    },
    {
        "name": "KMU-CAT Registration / Aggregate page",
        "url": "https://cat.kmu.edu.pk/aggregate.php",
        "institution": "Khyber Medical University, Peshawar",
        "category": "admissions",
        "is_official": True,
        "verification_status": Verification.VERIFIED,
        "verification_notes": "Official KMU-CAT entrance test portal with KMU's own aggregate calculator form.",
    },
    {
        "name": "KMU Centralized Admission — Private Sector Medical/Dental Colleges of KP",
        "url": "https://caspr.kmu.edu.pk/",
        "institution": "Khyber Medical University, Peshawar",
        "category": "admissions",
        "is_official": True,
        "verification_status": Verification.VERIFIED,
        "verification_notes": "Private-sector admissions portal; merit lists restate the 10/40/50 weightage.",
    },
    {
        "name": "KMU Postgraduate Admissions Portal",
        "url": "https://pgadmissions.kmu.edu.pk/",
        "institution": "Khyber Medical University, Peshawar",
        "category": "admissions",
        "is_official": True,
        "verification_status": Verification.UNVERIFIED,
        "verification_notes": "Linked from the official admissions page; contents not yet parsed, so no PG merit formula is stored.",
    },
    {
        "name": "KMU Constituent Institutes",
        "url": "https://kmu.edu.pk/institutes/constituent",
        "institution": "Khyber Medical University, Peshawar",
        "category": "institutions",
        "is_official": True,
        "verification_status": Verification.VERIFIED,
        "verification_notes": "Official list of KMU constituent institutes with contact details.",
    },
    {
        "name": "KMU Affiliated Institutes",
        "url": "https://kmu.edu.pk/institutes/affiliated",
        "institution": "Khyber Medical University, Peshawar",
        "category": "institutions",
        "is_official": True,
        "verification_status": Verification.VERIFIED,
        "verification_notes": "Official list of institutes affiliated with KMU, with contact details where published.",
    },
    {
        "name": "KMU Faculty by Institute",
        "url": "https://kmu.edu.pk/faculty_by_institute",
        "institution": "Khyber Medical University, Peshawar",
        "category": "faculty",
        "is_official": True,
        "verification_status": Verification.VERIFIED,
        "verification_notes": "Page indexes faculty by institute; individual faculty records were not extracted in this phase.",
    },
    {
        "name": "KMU Degree Programs — Undergraduate",
        "url": "https://kmu.edu.pk/programs/undergraduate",
        "institution": "Khyber Medical University, Peshawar",
        "category": "programs",
        "is_official": True,
        "verification_status": Verification.VERIFIED,
        "verification_notes": "Official undergraduate program list with offering institutes.",
    },
    {
        "name": "KMU Degree Programs — Postgraduate",
        "url": "https://kmu.edu.pk/programs/postgraduate",
        "institution": "Khyber Medical University, Peshawar",
        "category": "programs",
        "is_official": True,
        "verification_status": Verification.VERIFIED,
        "verification_notes": "Official postgraduate program list.",
    },
    {
        "name": "KMU Degree Programs — Diploma",
        "url": "https://kmu.edu.pk/programs/diploma",
        "institution": "Khyber Medical University, Peshawar",
        "category": "programs",
        "is_official": True,
        "verification_status": Verification.VERIFIED,
        "verification_notes": "Official diploma program list.",
    },
    {
        "name": "KMU Examination Guidelines (modular system)",
        "url": "https://kmu.edu.pk/examination/guidelines",
        "institution": "Khyber Medical University, Peshawar",
        "category": "curriculum",
        "is_official": True,
        "verification_status": Verification.UNVERIFIED,
        "verification_notes": "Official page; document contents not yet parsed in this phase.",
    },
    {
        "name": "KMU Calendar — Rules",
        "url": "https://kmu.edu.pk/kmu-calendar/rules",
        "institution": "Khyber Medical University, Peshawar",
        "category": "policies",
        "is_official": True,
        "verification_status": Verification.UNVERIFIED,
        "verification_notes": "Official rules index; downloads not yet parsed.",
    },
    {
        "name": "KMU Institute of Medical Sciences (Kohat) Prospectus 2022-23",
        "url": "https://kmu.edu.pk/storage/app/media/academics/KMU-IMS%20KOHAT%20PROSPECTUS%20%202022-23.pdf",
        "institution": "KMU Institute of Medical Sciences, Kohat",
        "category": "prospectus",
        "is_official": True,
        "verification_status": Verification.HISTORICAL,
        "verification_notes": "Historic prospectus (2022-23), linked from the KMU site; kept for reference only.",
    },
    {
        "name": "Pakistan Nursing & Midwifery Council — online services",
        "url": "https://online.pnmc.gov.pk/",
        "institution": "Pakistan Nursing & Midwifery Council (PNMC), Islamabad",
        "category": "regulator",
        "is_official": True,
        "verification_status": Verification.VERIFIED,
        "verification_notes": (
            "Regulator for nursing/midwifery registration. Distinguish PNMC recognition from KMU "
            "affiliation and HEC recognition. Address: PNMC Building, PM National Health Complex, "
            "NIH, Chak Shehzad, Islamabad; +92 51 9255805."
        ),
    },
    {
        "name": "Higher Education Commission of Pakistan",
        "url": "https://www.hec.gov.pk/",
        "institution": "Higher Education Commission, Pakistan",
        "category": "regulator",
        "is_official": True,
        "verification_status": Verification.VERIFIED,
        "verification_notes": "National higher-education regulator; degree attestation and equivalence guidance.",
    },
]

# --------------------------------------------------------------------------- #
# Admission cycles (dates exactly as published; nothing inferred)
# --------------------------------------------------------------------------- #
CYCLES: list[dict] = [
    {
        "name": "KMU BS (Allied Health) Undergraduate Admission — Peshawar Region",
        "session": "2026-27",
        "institution": "Khyber Medical University, Peshawar",
        "portal_url": "https://bsadmissions.kmu.edu.pk/",
        "form_open_date": date(2026, 6, 20),
        "form_close_date": date(2026, 10, 9),
        "status": "closed",
        "source_url": "https://bsadmissions.kmu.edu.pk/",
        "verification_status": Verification.VERIFIED,
    },
    {
        "name": "KMU Faculty of Nursing — BS Nursing Admission",
        "session": "2026-27",
        "institution": "Khyber Medical University, Peshawar",
        "portal_url": "https://nursing.kmu.edu.pk/",
        "form_open_date": date(2026, 6, 21),
        "form_close_date": date(2026, 10, 9),
        "status": "closed",
        "source_url": "https://nursing.kmu.edu.pk/",
        "verification_status": Verification.VERIFIED,
    },
    {
        "name": "MBBS/BDS Public Sector Medical & Dental Colleges of KP (Centralized)",
        "session": "2025-26",
        "institution": "Government of Khyber Pakhtunkhwa / KMU",
        "portal_url": "https://cas.kmu.edu.pk/",
        "form_open_date": None,
        "form_close_date": None,
        "status": "closed",
        "source_url": "https://cas.kmu.edu.pk/sitedocuments/Admission-Policy-Public-2025-26.pdf",
        "verification_status": Verification.VERIFIED,
    },
    {
        "name": "KMU Postgraduate Admissions",
        "session": "2026-27",
        "institution": "Khyber Medical University, Peshawar",
        "portal_url": "https://pgadmissions.kmu.edu.pk/",
        "form_open_date": None,
        "form_close_date": None,
        "status": "unknown",
        "source_url": "https://pgadmissions.kmu.edu.pk/",
        "verification_status": Verification.UNVERIFIED,
    },
]

# --------------------------------------------------------------------------- #
# Aggregate formulas
# --------------------------------------------------------------------------- #
FORMULAS: list[dict] = [
    {
        "name": "MBBS/BDS — Public Sector Medical & Dental Colleges of KP merit formula",
        "program_scope": "MBBS, BDS",
        "admission_session": "2025-26",
        "components": [
            {"key": "ssc", "label": "SSC / Matriculation or equivalent", "weight": 0.10, "input": "percent"},
            {"key": "hssc", "label": "FSc / HSSC (Pre-Medical) or equivalent (adjusted marks)", "weight": 0.40, "input": "percent"},
            {"key": "mdcat", "label": "MDCAT (PM&DC entrance test)", "weight": 0.50, "input": "percent"},
        ],
        "rounding": 5,
        "explanation": (
            "Official worked example in the policy: SSC 80% x 0.10 = 8.00000, FSc 80% x 0.40 = 32.00000, "
            "MDCAT 60% x 0.50 = 30.00000, final merit = 70.00000%. Final percentage is rounded to five decimals."
        ),
        "source_url": "https://cas.kmu.edu.pk/sitedocuments/Admission-Policy-Public-2025-26.pdf",
        "source_title": "ADMISSION POLICY 2025-26 — Public Sector Medical & Dental Colleges of Khyber Pakhtunkhwa",
        "verified": True,
        "status": FormulaStatus.ACTIVE,
        "effective_from": date(2025, 10, 1),
    },
    {
        "name": "BS / Allied Health Undergraduate — KMU-CAT merit formula (Peshawar Region)",
        "program_scope": "BS programs (Allied Health, Paramedical, DPT, Public Health, etc.)",
        "admission_session": "2026-27",
        "components": [
            {"key": "ssc", "label": "SSC / Matriculation or equivalent", "weight": 0.10, "input": "percent"},
            {"key": "hssc", "label": "FSc / HSSC (Pre-Medical) or equivalent", "weight": 0.50, "input": "percent"},
            {"key": "entrance", "label": "KMU-CAT entrance test", "weight": 0.40, "input": "percent"},
        ],
        "rounding": 5,
        "explanation": (
            "Published merit criteria on the official BS admission portal: SSC 10%, Intermediate/HSSC 50%, "
            "KMU-CAT entrance test 40%."
        ),
        "source_url": "https://bsadmissions.kmu.edu.pk/",
        "source_title": "KMU (BS) Undergraduate Centralized Admission Portal (Peshawar Region) — Merit Criteria",
        "verified": True,
        "status": FormulaStatus.ACTIVE,
        "effective_from": date(2026, 6, 20),
    },
    {
        "name": "BS Nursing (4 years) — KMU-CAT merit formula",
        "program_scope": "BS Nursing (4 years)",
        "admission_session": "2026-27",
        "components": [
            {"key": "ssc", "label": "SSC / Matriculation or equivalent", "weight": 0.10, "input": "percent"},
            {"key": "hssc", "label": "FSc / HSSC (Pre-Medical) or equivalent", "weight": 0.50, "input": "percent"},
            {"key": "entrance", "label": "KMU-CAT entrance test", "weight": 0.40, "input": "percent"},
        ],
        "rounding": 5,
        "explanation": (
            "Published merit criteria on the official Faculty of Nursing admission portal: SSC 10%, "
            "Intermediate/HSSC 50%, entrance test 40%."
        ),
        "source_url": "https://nursing.kmu.edu.pk/",
        "source_title": "KMU Faculty of Nursing — BS Nursing Centralized Admission Portal — Merit Criteria",
        "verified": True,
        "status": FormulaStatus.ACTIVE,
        "effective_from": date(2026, 6, 21),
    },
    {
        "name": "Postgraduate programs — merit formula (not yet retrieved)",
        "program_scope": "Postgraduate programs",
        "admission_session": "2026-27",
        "components": [],
        "rounding": 5,
        "explanation": None,
        "source_url": "https://pgadmissions.kmu.edu.pk/",
        "source_title": "KMU Postgraduate Admissions Portal",
        "verified": False,
        "status": FormulaStatus.PENDING,
        "verification_notes": (
            "The postgraduate merit formula has not been retrieved from an official document yet. "
            "The calculator deliberately refuses to compute with this entry."
        ),
    },
]

# --------------------------------------------------------------------------- #
# Eligibility rules
# --------------------------------------------------------------------------- #
RULES: list[dict] = [
    {
        "cycle": "MBBS/BDS Public Sector Medical & Dental Colleges of KP (Centralized)",
        "program_scope": "MBBS",
        "rule_type": RuleType.ELIGIBILITY,
        "title": "MBBS basic eligibility (HSSC and MDCAT)",
        "text": (
            "Minimum 60% marks in HSSC/equivalent with Biology and Chemistry plus Physics or Mathematics; "
            "MDCAT conducted by PM&DC with at least 55% marks. Equivalence (if applicable) must be produced "
            "by the closing date. Source: Admission Policy 2025-26, section E."
        ),
        "min_hssc_percent": 60.0,
        "min_mdcat_percent": 55.0,
        "required_subjects": ["Biology", "Chemistry", "Physics or Mathematics"],
        "source_url": "https://cas.kmu.edu.pk/sitedocuments/Admission-Policy-Public-2025-26.pdf",
        "verification_status": Verification.VERIFIED,
    },
    {
        "cycle": "MBBS/BDS Public Sector Medical & Dental Colleges of KP (Centralized)",
        "program_scope": "BDS",
        "rule_type": RuleType.ELIGIBILITY,
        "title": "BDS basic eligibility (HSSC and MDCAT)",
        "text": (
            "Minimum 60% marks in HSSC/equivalent with the required science subjects; MDCAT with at least "
            "50% marks. Source: Admission Policy 2025-26."
        ),
        "min_hssc_percent": 60.0,
        "min_mdcat_percent": 50.0,
        "required_subjects": ["Biology", "Chemistry", "Physics or Mathematics"],
        "source_url": "https://cas.kmu.edu.pk/sitedocuments/Admission-Policy-Public-2025-26.pdf",
        "verification_status": Verification.VERIFIED,
    },
    {
        "cycle": "KMU BS (Allied Health) Undergraduate Admission — Peshawar Region",
        "program_scope": "BS programs",
        "rule_type": RuleType.ELIGIBILITY,
        "title": "BS (Allied Health) eligibility for session 2026-27",
        "text": (
            "FSc (Pre-Medical) or equivalent with a minimum of 50% marks for BS programs; appearance in "
            "KMU-CAT 2026 is mandatory. In-service candidates need at least two years of experience and must "
            "apply through proper channel. Diploma holders must provide an IBCC equivalence certificate."
        ),
        "min_hssc_percent": 50.0,
        "min_entrance_percent": None,
        "required_subjects": ["Biology", "Chemistry"],
        "source_url": "https://bsadmissions.kmu.edu.pk/",
        "verification_status": Verification.VERIFIED,
    },
    {
        "cycle": "KMU BS (Allied Health) Undergraduate Admission — Peshawar Region",
        "program_scope": "Doctor of Physical Therapy (DPT)",
        "rule_type": RuleType.ELIGIBILITY,
        "title": "DPT eligibility for session 2026-27",
        "text": (
            "FSc (Pre-Medical) or equivalent with a minimum of 60% marks for the DPT program; KMU-CAT 2026 "
            "appearance is mandatory. Candidates with FSc (Pre-Engineering) may apply to BS Prosthetics & Orthotics."
        ),
        "min_hssc_percent": 60.0,
        "required_subjects": ["Biology", "Chemistry"],
        "source_url": "https://bsadmissions.kmu.edu.pk/",
        "verification_status": Verification.VERIFIED,
    },
    {
        "cycle": "KMU Faculty of Nursing — BS Nursing Admission",
        "program_scope": "BS Nursing",
        "rule_type": RuleType.ELIGIBILITY,
        "title": "BS Nursing (4 years) eligibility for session 2026-27",
        "text": (
            "FSc (Pre-Medical) or equivalent with a minimum of 50% marks; age between 17 and 35 years; "
            "candidates must have appeared in KMU-CAT 2026. Candidates from KP including merged districts, "
            "AJK, Gilgit-Baltistan and other provinces may apply (other provinces must appear in KMU-CAT)."
        ),
        "min_hssc_percent": 50.0,
        "required_subjects": ["Biology", "Chemistry"],
        "source_url": "https://nursing.kmu.edu.pk/",
        "verification_status": Verification.VERIFIED,
    },
    {
        "cycle": "MBBS/BDS Public Sector Medical & Dental Colleges of KP (Centralized)",
        "program_scope": "MBBS, BDS",
        "rule_type": RuleType.QUOTA,
        "title": "Seat categories in the 2025-26 policy",
        "text": (
            "The policy defines open merit, various provincial/merged-district categories, self-finance, "
            "minority, persons with special ability, overseas/OPF and a small number of special-category seats. "
            "Each category has its own eligibility conditions in the policy document."
        ),
        "source_url": "https://cas.kmu.edu.pk/sitedocuments/Admission-Policy-Public-2025-26.pdf",
        "verification_status": Verification.VERIFIED,
    },
]

POLICIES: list[dict] = [
    {
        "title": "KMU Admission Policy 2025-26 (Public Sector Medical & Dental Colleges of KP)",
        "category": "admissions",
        "summary": (
            "The applicable admission policy document: defines the 10/40/50 merit weightage, eligibility "
            "thresholds, seat categories, scrutiny and merit-list process, and states that admissions are "
            "provisional and subject to PM&DC regulations."
        ),
        "source_url": "https://cas.kmu.edu.pk/sitedocuments/Admission-Policy-Public-2025-26.pdf",
        "effective_date": date(2025, 10, 1),
        "verification_status": Verification.VERIFIED,
    },
    {
        "title": "KMU-CAT entrance test requirement (BS and Nursing admissions)",
        "category": "admissions",
        "summary": (
            "The BS and Nursing admission portals state that appearing in KMU-CAT is mandatory for admission "
            "to eligible BS degree programs, and that KMU-CAT registration is handled through the KMU-CAT portal."
        ),
        "source_url": "https://cat.kmu.edu.pk/",
        "effective_date": None,
        "verification_status": Verification.VERIFIED,
    },
    {
        "title": "PNMC regulatory scope (nursing and midwifery registration)",
        "category": "regulatory",
        "summary": (
            "PNMC maintains the national register of nurses, midwives and LHVs and the recognition of nursing "
            "institutes. PNMC recognition is a separate question from KMU affiliation and from HEC degree "
            "recognition; students should check all applicable bodies."
        ),
        "source_url": "https://online.pnmc.gov.pk/",
        "effective_date": None,
        "verification_status": Verification.VERIFIED,
    },
    {
        "title": "HEC degree recognition and attestation",
        "category": "regulatory",
        "summary": (
            "HEC handles degree attestation and equivalence guidance; a university's HEC recognition is distinct "
            "from programme-level professional accreditation."
        ),
        "source_url": "https://www.hec.gov.pk/",
        "effective_date": None,
        "verification_status": Verification.VERIFIED,
    },
]

# Pages archived into the knowledge base (fetched, cleaned, chunked, embedded).
INGEST_PAGES: list[dict] = [
    {"url": "https://kmu.edu.pk/", "title": "Khyber Medical University — Home", "doc_type": DocType.WEBPAGE, "institution": "Khyber Medical University, Peshawar"},
    {"url": "https://kmu.edu.pk/admissions", "title": "KMU — Admissions", "doc_type": DocType.WEBPAGE, "institution": "Khyber Medical University, Peshawar"},
    {"url": "https://kmu.edu.pk/institutes/constituent", "title": "KMU — Constituent Institutes", "doc_type": DocType.WEBPAGE, "institution": "Khyber Medical University, Peshawar"},
    {"url": "https://kmu.edu.pk/institutes/affiliated", "title": "KMU — Affiliated Institutes", "doc_type": DocType.WEBPAGE, "institution": "Khyber Medical University, Peshawar"},
    {"url": "https://kmu.edu.pk/programs/undergraduate", "title": "KMU — Undergraduate Programs", "doc_type": DocType.WEBPAGE, "institution": "Khyber Medical University, Peshawar"},
    {"url": "https://kmu.edu.pk/programs/postgraduate", "title": "KMU — Postgraduate Programs", "doc_type": DocType.WEBPAGE, "institution": "Khyber Medical University, Peshawar"},
    {"url": "https://kmu.edu.pk/programs/diploma", "title": "KMU — Diploma Programs", "doc_type": DocType.WEBPAGE, "institution": "Khyber Medical University, Peshawar"},
    {"url": "https://kmu.edu.pk/faculty_by_institute", "title": "KMU — Faculty by Institute", "doc_type": DocType.WEBPAGE, "institution": "Khyber Medical University, Peshawar"},
    {"url": "https://bsadmissions.kmu.edu.pk/", "title": "KMU BS Undergraduate Admission Portal (Peshawar Region) 2026-27", "doc_type": DocType.WEBPAGE, "institution": "Khyber Medical University, Peshawar", "admission_cycle": "2026-27"},
    {"url": "https://nursing.kmu.edu.pk/", "title": "KMU Faculty of Nursing — BS Nursing Admission Portal 2026-27", "doc_type": DocType.WEBPAGE, "institution": "Khyber Medical University, Peshawar", "admission_cycle": "2026-27"},
    {"url": "https://online.pnmc.gov.pk/", "title": "Pakistan Nursing & Midwifery Council — Online Services", "doc_type": DocType.WEBPAGE, "institution": "Pakistan Nursing & Midwifery Council"},
    {"url": "https://www.hec.gov.pk/", "title": "Higher Education Commission of Pakistan — Home", "doc_type": DocType.WEBPAGE, "institution": "Higher Education Commission, Pakistan"},
    {
        "url": "https://cas.kmu.edu.pk/sitedocuments/Admission-Policy-Public-2025-26.pdf",
        "title": "KMU Admission Policy 2025-26 (Public Sector Medical & Dental Colleges of KP)",
        "doc_type": DocType.PDF,
        "institution": "Government of Khyber Pakhtunkhwa / KMU / PM&DC",
        "admission_cycle": "2025-26",
    },
    {
        "url": "https://kmu.edu.pk/storage/app/media/academics/KMU-IMS%20KOHAT%20PROSPECTUS%20%202022-23.pdf",
        "title": "KMU Institute of Medical Sciences (Kohat) Prospectus 2022-23",
        "doc_type": DocType.PROSPECTUS,
        "institution": "KMU Institute of Medical Sciences, Kohat",
    },
]
