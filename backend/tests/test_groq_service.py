import json
from types import SimpleNamespace

import pytest

from app.services.groq import GroqInvalidResponseError, GroqJobAnalyzer

PYTHON_BACKEND_JD = """
We are hiring a Senior Python Backend Engineer in Bengaluru.
The engineer will build FastAPI services backed by PostgreSQL and Docker.
Candidates must have 4 to 7 years of backend development experience.
""".strip()

VALID_ANALYSIS = {
    "job_title": "Senior Python Backend Engineer",
    "skills": ["Python", "FastAPI", "PostgreSQL", "Docker"],
    "location": "Bengaluru",
    "minimum_experience": 4,
    "maximum_experience": 7,
    "seniority": "Senior",
    "search_keywords": "Senior Python Backend Engineer FastAPI PostgreSQL Docker Bengaluru",
}


class FakeCompletions:
    def __init__(self, outputs: list[str]) -> None:
        self.outputs = iter(outputs)
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        content = next(self.outputs)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
        )


def make_analyzer(outputs: list[str]) -> tuple[GroqJobAnalyzer, FakeCompletions]:
    completions = FakeCompletions(outputs)
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    analyzer = GroqJobAnalyzer(
        client=client, model="openai/gpt-oss-120b"  # type: ignore[arg-type]
    )
    return analyzer, completions


def test_analyzer_removes_markdown_fences_and_validates_output() -> None:
    analyzer, completions = make_analyzer([f"```json\n{json.dumps(VALID_ANALYSIS)}\n```"])

    result = analyzer.analyze(PYTHON_BACKEND_JD)

    assert result.job_title == "Senior Python Backend Engineer"
    assert result.skills == ["Python", "FastAPI", "PostgreSQL", "Docker"]
    assert len(completions.calls) == 1
    assert completions.calls[0]["model"] == "openai/gpt-oss-120b"
    assert completions.calls[0]["temperature"] == 0
    assert completions.calls[0]["response_format"] == {"type": "json_object"}


def test_analyzer_retries_once_with_json_correction_prompt() -> None:
    analyzer, completions = make_analyzer(["not-json", json.dumps(VALID_ANALYSIS)])

    result = analyzer.analyze(PYTHON_BACKEND_JD)

    assert result.minimum_experience == 4
    assert len(completions.calls) == 2
    correction_prompt = completions.calls[1]["messages"][1]["content"]
    assert "Correct the invalid output" in correction_prompt
    assert "not-json" in correction_prompt


def test_analyzer_raises_after_two_invalid_outputs() -> None:
    analyzer, completions = make_analyzer(["not-json", '{"job_title": 42}'])

    with pytest.raises(GroqInvalidResponseError):
        analyzer.analyze(PYTHON_BACKEND_JD)

    assert len(completions.calls) == 2
