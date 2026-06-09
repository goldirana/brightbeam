"""Prompt registry — loads prompts from text files via ConfigManager.

All prompts live in the prompts/ folder as .txt files.
Variables are substituted from config.yaml.
To change a prompt: edit the .txt file. To change a variable: edit config.yaml.
"""

from src.config.manager import ConfigManager


def get_prompt(category: str, transcript: str) -> tuple[str, str]:
    """Return (system_prompt, user_prompt) for a given category and transcript."""
    cfg = ConfigManager.get()
    system_prompt = cfg.get_system_prompt(category)
    user_prompt = f"Summarise the following insurance call transcript:\n\n{transcript}"
    return system_prompt, user_prompt


def get_judge_prompt(transcript: str, summary: str, entities: list[str]) -> tuple[str, str]:
    """Return (system_prompt, user_prompt) for the LLM judge evaluation."""
    cfg = ConfigManager.get()
    system_prompt = cfg.get_judge_system_prompt()
    user_prompt = cfg.get_judge_evaluate_prompt(
        transcript=transcript,
        summary=summary,
        entities=", ".join(entities),
    )
    return system_prompt, user_prompt


def get_retry_prompt(transcript: str, previous_summary: str, feedback: str) -> tuple[str, str]:
    """Return (system_prompt, user_prompt) for a retry with judge feedback."""
    cfg = ConfigManager.get()
    system_prompt = cfg.get_system_prompt("general_enquiry")
    user_prompt = cfg.get_retry_prompt(
        transcript=transcript,
        previous_summary=previous_summary,
        feedback=feedback,
    )
    return system_prompt, user_prompt
