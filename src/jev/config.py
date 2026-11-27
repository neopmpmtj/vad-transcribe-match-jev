"""Question asked of Jev, and the cutoff for yes."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    """Whether an entry is exactly one request.

    model is the TypeSafe model name. yes_at is the probability at or above
    which the answer is yes. instructions is the question. true_case and
    false_case describe the two sides.
    """

    model: str = "jev-latest"
    yes_at: float = 0.5
    instructions: str = "Is this entry exactly one request?"
    true_case: str = (
        "The whole entry asks for one thing. It is one question, or one "
        "instruction, and nothing else. Asking the time is one request. "
        "Asking what the weather is like nearby is one request. Checking "
        "the weather for the next three days is one request. Making a "
        "calendar entry is one request. A standalone question is one "
        "request. Polite wording, such as could you, is still one request."
    )
    false_case: str = (
        "The entry is a journal paragraph, an observation, an exclamation, "
        "or a greeting that asks for nothing. The entry asks for two things, "
        "such as the time and a calendar entry. A journal paragraph stays on "
        "this side when one sentence inside it is a question."
    )
