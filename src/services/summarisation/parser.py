"""Parser for converting raw LLM text output into structured CallSummary."""

import re

from src.models.summary import CallSummary, NextSteps, VehicleDamage


def parse_summary_text(text: str) -> CallSummary:
    """Parse the raw summary text into a structured Pydantic model."""
    sections = _split_sections(text)

    # Parse caller
    caller = sections.get("caller", "Unknown")

    # Parse subject
    subject = sections.get("subject", "Unknown")

    # Parse executive summary
    executive_summary = sections.get("executive summary", "")

    # Parse next steps
    next_steps_raw = sections.get("next steps", "")
    next_steps = _parse_next_steps(next_steps_raw)

    # Parse follow-up
    follow_up_required, follow_up_reason = _parse_follow_up(sections, text)

    # Parse optional sections
    liability = sections.get("liability summary")
    negotiation = sections.get("negotiation summary")
    vehicle_damage = _parse_vehicle_damage(sections.get("vehicle damage"))
    injury = sections.get("injury")
    property_damage = sections.get("property")

    # Clean injury if it has "Treatment:" prefix
    if injury and injury.lower().startswith("treatment:"):
        injury = injury[len("treatment:"):].strip()

    return CallSummary(
        caller=caller,
        subject=subject,
        executive_summary=executive_summary,
        next_steps=next_steps,
        follow_up_required=follow_up_required,
        follow_up_reason=follow_up_reason,
        liability_summary=liability,
        negotiation_summary=negotiation,
        vehicle_damage=vehicle_damage,
        injury=injury,
        property_damage=property_damage,
    )


def _split_sections(text: str) -> dict[str, str]:
    """Split summary text into named sections."""
    sections: dict[str, str] = {}

    # Handle Caller line specially (first line)
    lines = text.strip().split("\n")
    current_section = None
    current_content: list[str] = []

    for line in lines:
        # Check if line starts a new section
        if line.startswith("Caller:"):
            sections["caller"] = line[len("Caller:"):].strip()
            continue

        section_match = re.match(
            r"^(Subject|Executive Summary|Next Steps|Liability Summary|Negotiation Summary|Vehicle Damage|Injury|Property):\s*(.*)",
            line,
            re.IGNORECASE,
        )

        if section_match:
            # Save previous section
            if current_section:
                sections[current_section] = "\n".join(current_content).strip()

            current_section = section_match.group(1).lower()
            first_line = section_match.group(2).strip()
            current_content = [first_line] if first_line else []
        elif current_section:
            current_content.append(line)

    # Save last section
    if current_section:
        sections[current_section] = "\n".join(current_content).strip()

    return sections


def _parse_next_steps(raw: str) -> NextSteps:
    """Parse next steps section into structured model."""
    company = "None"
    other = "None"

    for line in raw.split("\n"):
        line_clean = line.strip()
        if re.match(r"^(COMPANY|Company):", line_clean, re.IGNORECASE):
            company = re.sub(r"^(COMPANY|Company):\s*", "", line_clean, flags=re.IGNORECASE)
        elif re.match(r"^Other:", line_clean, re.IGNORECASE):
            other = re.sub(r"^Other:\s*", "", line_clean, flags=re.IGNORECASE)

    return NextSteps(company=company, other=other)


def _parse_vehicle_damage(raw: str | None) -> VehicleDamage | None:
    """Parse vehicle damage section if present."""
    if not raw:
        return None

    status = "Unknown"
    towage = "None"
    car_hire = "None"

    for line in raw.split("\n"):
        line_clean = line.strip()
        if line_clean.lower().startswith("vehicle status:"):
            status = line_clean[len("vehicle status:"):].strip()
        elif line_clean.lower().startswith("towage:"):
            towage = line_clean[len("towage:"):].strip()
        elif line_clean.lower().startswith("car hire:"):
            car_hire = line_clean[len("car hire:"):].strip()

    return VehicleDamage(vehicle_status=status, towage=towage, car_hire=car_hire)


def _parse_follow_up(sections: dict[str, str], raw_text: str) -> tuple[bool, str | None]:
    """Parse Follow-Up Required from the raw text."""
    # Look for "Follow-Up Required: Yes/No" line anywhere in text
    follow_up = False
    reason = None

    for line in raw_text.split("\n"):
        line_clean = line.strip()
        if line_clean.lower().startswith("follow-up required:"):
            value = line_clean.split(":", 1)[1].strip().lower()
            follow_up = value in ("yes", "true", "y")
        elif line_clean.lower().startswith("reason:") and follow_up:
            reason = line_clean.split(":", 1)[1].strip()

    return follow_up, reason
