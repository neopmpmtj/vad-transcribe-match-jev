"""OpenAI endpoint, model, and the length cap for case edits."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    """Where a case edit is requested, and how long the two cases may be.

    base_url is the OpenAI API root. model is the model name.
    max_cases_chars is the maximum length of true_case and false_case
    added together. The developer edits that number in this file.
    shrink_attempts is how many silent rewrites are allowed when a draft
    is over that length.
    """

    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4.1-mini"
    max_cases_chars: int = 1500
    shrink_attempts: int = 3
