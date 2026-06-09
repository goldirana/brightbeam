import json

from src.models.validation import QualityIssue, QualityScore
from src.services.summarisation.base import BaseLLMProvider
from src.services.summarisation.prompt_registry import get_judge_prompt


async def evaluate_quality(
    transcript_id: str,
    transcript: str,
    summary_text: str,
    entities: list[str],
    llm: BaseLLMProvider,
) -> QualityScore:
    """Layer 3: LLM-as-judge evaluation of summary quality."""
    system_prompt, user_prompt = get_judge_prompt(transcript, summary_text, entities)

    raw_response = await llm.generate(user_prompt, system_prompt)

    # Parse JSON from LLM response
    try:
        # Handle potential markdown code blocks in response
        clean = raw_response.strip()
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[1].rsplit("```", 1)[0]
        data = json.loads(clean)
    except (json.JSONDecodeError, IndexError):
        # If judge response is unparseable, return conservative score
        return QualityScore(
            transcript_id=transcript_id,
            overall_score=0.5,
            issues_found=[QualityIssue(
                check="judge_parse_error",
                severity="warning",
                description="Could not parse judge response",
                suggestion="Manual review recommended",
            )],
        )

    scores = data.get("scores", {})
    issues_raw = data.get("issues", [])

    issues = [
        QualityIssue(
            check=i.get("check", "unknown"),
            severity=i.get("severity", "warning"),
            description=i.get("description", ""),
            suggestion=i.get("suggestion", ""),
        )
        for i in issues_raw
    ]

    return QualityScore(
        transcript_id=transcript_id,
        issue_and_actions_clear=scores.get("issue_and_actions_clear", 0.0),
        critical_facts_accurate=scores.get("critical_facts_accurate", 0.0),
        handoff_ready=scores.get("handoff_ready", 0.0),
        professional_tone=scores.get("professional_tone", 0.0),
        within_char_limit=scores.get("within_char_limit", True),
        overall_score=data.get("overall_score", 0.0),
        issues_found=issues,
    )
