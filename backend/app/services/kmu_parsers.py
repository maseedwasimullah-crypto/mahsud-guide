"""Parsers for the structured KMU web tables (programs, institutes).

Only used on our own archived copies / freshly fetched official pages. The
markup is a plain HTML table: S.No | Name | Contact Options | Details.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from bs4 import BeautifulSoup

PHONE_RE = re.compile(r"(?:\+?92|0)[\s\-]?\d[\d\s\-()]{6,}")
EMAIL_RE = re.compile(r"[\w.\-+]+@[\w.\-]+\.\w+")
WEBSITE_RE = re.compile(r"(?:(?:https?://)?(?:www\.)?[a-z0-9\-]+(?:\.[a-z]{2,}){1,3}(?:/[\w\-./?%&=+]*)?)", re.I)

CITY_HINTS = [
    "Peshawar", "Abbottabad", "Mardan", "Swat", "Saidu Sharif", "Buner", "Charsadda",
    "Nowshera", "Kohat", "Bannu", "D.I.Khan", "D.I. Khan", "Karak", "Haripur", "Mansehra",
    "Swabi", "Dir Upper", "Dir Lower", "Timergara", "Chakdara", "Batkhela", "Malakand",
    "Shangla", "Chitral", "Lower Chitral", "Parachinar", "Kurram", "Islamabad", "Matta",
    "Manglawar", "Shergarh", "Shabqadar", "Daggar", "Swari Buner",
]


@dataclass
class ParsedInstitution:
    name: str
    detail_url: str | None = None
    website: str | None = None
    phone: str | None = None
    email: str | None = None
    city: str | None = None


@dataclass
class ParsedProgram:
    title: str
    detail_url: str | None = None
    institutes: list[str] = field(default_factory=list)


def _clean_cell_text(cell) -> str:
    text = cell.get_text(" ", strip=True)
    return re.sub(r"\[email\s*protected\]", "", text).strip()


def _extract_city(name: str) -> str | None:
    for city in sorted(CITY_HINTS, key=len, reverse=True):
        if city.lower() in name.lower():
            return city
    parts = [p.strip() for p in name.split(",") if p.strip()]
    if len(parts) > 1:
        return parts[-1]
    return None


def parse_institution_table(html: str) -> list[ParsedInstitution]:
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")
    if table is None:
        return []
    results: list[ParsedInstitution] = []
    for row in table.find_all("tr"):
        cells = row.find_all(["td", "th"])
        if len(cells) < 2:
            continue
        name = _clean_cell_text(cells[1])
        if not name or name.lower().startswith(("institute name", "program title")):
            continue
        detail_url = None
        for link in row.find_all("a"):
            href = link.get("href") or ""
            if "/institute/" in href or "/program/" in href:
                detail_url = href if href.startswith("http") else f"https://kmu.edu.pk{href}"
        contact_text = _clean_cell_text(cells[2]) if len(cells) > 2 else ""
        website = None
        for match in WEBSITE_RE.finditer(contact_text):
            candidate = match.group(0)
            if "@" in candidate:
                continue
            website = candidate if candidate.startswith("http") else f"http://{candidate}"
            break
        phone_match = PHONE_RE.search(contact_text)
        email_match = EMAIL_RE.search(contact_text)
        results.append(
            ParsedInstitution(
                name=name,
                detail_url=detail_url,
                website=website,
                phone=phone_match.group(0).strip() if phone_match else None,
                email=email_match.group(0) if email_match else None,
                city=_extract_city(name),
            )
        )
    return results


def parse_program_table(html: str) -> list[ParsedProgram]:
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")
    if table is None:
        return []
    results: list[ParsedProgram] = []
    for row in table.find_all("tr"):
        cells = row.find_all(["td", "th"])
        if len(cells) < 2:
            continue
        title = _clean_cell_text(cells[1])
        if not title or title.lower().startswith("program title"):
            continue
        detail_url = None
        for link in row.find_all("a"):
            href = link.get("href") or ""
            if "/program/" in href:
                detail_url = href if href.startswith("http") else f"https://kmu.edu.pk{href}"
        institutes: list[str] = []
        if len(cells) > 2:
            for li in cells[2].find_all("li"):
                value = _clean_cell_text(li)
                if value and value.lower() != "null":
                    institutes.append(value)
            if not institutes:
                value = _clean_cell_text(cells[2])
                if value and value.lower() != "null":
                    institutes.append(value)
        results.append(ParsedProgram(title=title, detail_url=detail_url, institutes=institutes))
    return results


def classify_affiliated_institution(name: str) -> str:
    lowered = name.lower()
    if any(
        keyword in lowered
        for keyword in (
            "college of nursing",
            "nursing college",
            "institute of nursing",
            "school of nursing",
            "nursing institute",
            "nursing & ",
            "nursing and ",
            "midwifery",
        )
    ):
        return "affiliated_nursing_college"
    if "medical college" in lowered or "medical & dental" in lowered or "medical and dental" in lowered:
        return "affiliated_medical_college"
    if "dental" in lowered:
        return "affiliated_dental_college"
    if "homoeopathic" in lowered or "homeopathic" in lowered:
        return "affiliated_homeopathic_college"
    if "pharmacy" in lowered:
        return "affiliated_pharmacy_college"
    if "rehabilitation" in lowered or "physiotherapy" in lowered:
        return "affiliated_rehabilitation_college"
    return "affiliated_health_sciences_institute"
