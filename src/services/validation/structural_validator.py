import re

from src.models.summary import CallSummary
from src.models.validation import QualityIssue


def validate_structure(summary: CallSummary) -> tuple[bool, list[QualityIssue]]:
    """Layer 1: Structural validation using Pydantic model + format rules."""
    issues = []

    # Check character limit
    rendered = summary.render()
    if len(rendered) > 1500:
        issues.append(QualityIssue(
            check="char_limit",
            severity="critical",
            description=f"Summary is {len(rendered)} characters, exceeds 1500 limit",
            suggestion="Reduce executive summary or remove redundant details",
        ))

    # Check caller has relationship and direction
    caller = summary.caller.lower()
    relationships = ["policyholder", "third party", "solicitor", "family member", "representative", "claimant"]
    directions = ["inbound", "outbound"]

    if not any(r in caller for r in relationships):
        issues.append(QualityIssue(
            check="caller_format",
            severity="warning",
            description="Caller line missing relationship identifier",
            suggestion="Include relationship: policyholder, third party, solicitor, etc.",
        ))

    if not any(d in caller for d in directions):
        issues.append(QualityIssue(
            check="caller_format",
            severity="warning",
            description="Caller line missing call direction (inbound/outbound)",
            suggestion="Include call direction",
        ))

    # Check subject is single line
    if "\n" in summary.subject:
        issues.append(QualityIssue(
            check="subject_format",
            severity="minor",
            description="Subject should be a single line",
            suggestion="Condense to one concise line",
        ))

    # Check next steps
    if not summary.next_steps.company.strip():
        issues.append(QualityIssue(
            check="next_steps",
            severity="critical",
            description="Missing company next steps",
            suggestion="Always include what the company needs to do",
        ))

    is_valid = not any(i.severity == "critical" for i in issues)
    return is_valid, issues
