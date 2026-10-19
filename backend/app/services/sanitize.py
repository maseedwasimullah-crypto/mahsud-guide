"""Prompt-injection defence for retrieved (untrusted) content.

Everything fetched from the web is treated as data, never as instructions:
* instruction-like lines are neutralised before the text reaches a prompt,
* the text is wrapped in explicit data delimiters,
* the system prompt states that fenced content cannot change the rules.
"""

from __future__ import annotations

import re

INJECTION_PATTERNS = [
    re.compile(r"(?i)ignore (all |any )?(previous|prior|above|earlier) (instructions|prompts|rules)"),
    re.compile(r"(?i)disregard (all |any )?(previous|prior|above) (instructions|rules)"),
    re.compile(r"(?i)you are (now|no longer)\b"),
    re.compile(r"(?i)system\s*prompt"),
    re.compile(r"(?i)reveal (your|the) (system )?(prompt|instructions|api key|secret)"),
    re.compile(r"(?i)(print|show|output|leak|expose) (the )?(api[_ -]?key|secret|token|password)"),
    re.compile(r"(?i)new instructions\s*:"),
    re.compile(r"(?i)assistant\s*:"),
    re.compile(r"(?i)\bexecute\b.*\b(command|shell|sql)\b"),
    re.compile(r"<\|.*?\|>"),
]

UNTRUSTED_OPEN = "<<<BEGIN_UNTRUSTED_SOURCE_DATA>>>"
UNTRUSTED_CLOSE = "<<<END_UNTRUSTED_SOURCE_DATA>>>"


def strip_control_chars(text: str) -> str:
    return "".join(ch for ch in text if ch == "\n" or ch == "\t" or ord(ch) >= 32)


def sanitize_untrusted(text: str, *, max_chars: int = 4000) -> tuple[str, list[str]]:
    """Return (sanitised_text, list_of_flagged_patterns)."""
    text = strip_control_chars(text or "")
    flagged: list[str] = []
    safe_lines: list[str] = []
    for line in text.split("\n"):
        if any(pattern.search(line) for pattern in INJECTION_PATTERNS):
            flagged.append(line.strip()[:200])
            safe_lines.append("[line removed: contained instruction-like content]")
        else:
            safe_lines.append(line)
    cleaned = "\n".join(safe_lines)[:max_chars]
    return cleaned, flagged


def fence(text: str) -> str:
    return f"{UNTRUSTED_OPEN}\n{text}\n{UNTRUSTED_CLOSE}"


def contains_instruction_like_text(text: str) -> bool:
    return any(pattern.search(text or "") for pattern in INJECTION_PATTERNS)
