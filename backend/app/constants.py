"""Shared vocabulary for verification states and institutional classification.

These values are deliberately plain strings so the schema stays portable between
SQLite (development) and PostgreSQL (production).
"""

from __future__ import annotations


class Verification:
    """How much trust a record has earned from the research/ingestion process."""

    VERIFIED = "verified"          # traced to an official document/page, checked
    UNVERIFIED = "unverified"      # collected but not confirmed against an official source
    CONFLICTING = "conflicting"    # official sources disagree; see notes
    HISTORICAL = "historical"      # was official but superseded by a newer notice
    DEMO = "demo"                  # synthetic demonstration record, never official


class InstitutionType:
    UNIVERSITY = "university"
    CONSTITUENT_INSTITUTE = "constituent_institute"
    AFFILIATED_COLLEGE = "affiliated_college"
    REGULATORY_BODY = "regulatory_body"
    OTHER = "other"


class DegreeLevel:
    UNDERGRADUATE = "undergraduate"
    POSTGRADUATE = "postgraduate"
    DIPLOMA = "diploma"


class FormulaStatus:
    ACTIVE = "active"        # formula may be used by the calculator
    PENDING = "pending"      # collected, not yet verified -> calculator refuses it
    SUPERSEDED = "superseded"  # historical formula, kept for reference


class RuleType:
    ELIGIBILITY = "eligibility"
    QUOTA = "quota"
    PROCEDURE = "procedure"
    FEE = "fee"
    DOCUMENT = "document"


class DocType:
    WEBPAGE = "webpage"
    PDF = "pdf"
    DOCX = "docx"
    NOTICE = "notice"
    POLICY = "policy"
    PROSPECTUS = "prospectus"
    CURRICULUM = "curriculum"


class Role:
    ADMIN = "admin"
    REVIEWER = "reviewer"
