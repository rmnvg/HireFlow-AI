import json
import re
from typing import Any

from groq import Groq
from pydantic import ValidationError

from app.schemas import JobAnalysis

MODEL_INSTRUCTIONS = """You extract structured hiring requirements from job descriptions.
Return only one valid JSON object with exactly these keys:
job_title, skills, location, minimum_experience, maximum_experience, seniority, search_keywords.

Rules:
- Never invent or infer facts that are absent from the job description.
- Use an empty string for job_title when no title is explicitly stated.
- Use an empty list for skills when no skills are explicitly stated.
- Use null for location, experience values, or seniority when they are not explicitly stated.
- Experience values must be non-negative whole numbers representing years.
- search_keywords must contain only terms explicitly present in the title, skills, location,
  experience, or seniority. Use an empty string when no useful terms are present.
- Do not include Markdown, commentary, explanations, or additional keys.
"""


class GroqServiceError(Exception):
    """Base exception for safe upstream failure handling."""


class GroqUnavailableError(GroqServiceError):
    """The Groq request could not be completed."""


class GroqInvalidResponseError(GroqServiceError):
    """Groq returned invalid structured data twice."""


class GroqJobAnalyzer:
    def __init__(self, client: Groq, model: str) -> None:
        self._client = client
        self._model = model

    def analyze(self, description: str) -> JobAnalysis:
        first_output = self._complete(
            [
                {"role": "system", "content": MODEL_INSTRUCTIONS},
                {"role": "user", "content": f"Extract this job description:\n\n{description}"},
            ]
        )

        try:
            return self._parse(first_output)
        except (json.JSONDecodeError, ValidationError):
            corrected_output = self._complete(
                [
                    {"role": "system", "content": MODEL_INSTRUCTIONS},
                    {
                        "role": "user",
                        "content": (
                            "Correct the invalid output below into the required JSON object. "
                            "Use only facts present in the original job description.\n\n"
                            f"Original job description:\n{description}\n\n"
                            f"Invalid output:\n{first_output}"
                        ),
                    },
                ]
            )
            try:
                return self._parse(corrected_output)
            except (json.JSONDecodeError, ValidationError) as exc:
                raise GroqInvalidResponseError(
                    "Groq returned invalid job analysis data after one retry"
                ) from exc

    def _complete(self, messages: list[dict[str, str]]) -> str:
        try:
            completion = self._client.chat.completions.create(
                model=self._model,
                temperature=0,
                messages=messages,  # type: ignore[arg-type]
                response_format={"type": "json_object"},
            )
            content = completion.choices[0].message.content
        except Exception as exc:
            # Do not include SDK errors because they may contain request metadata.
            raise GroqUnavailableError("Groq request failed") from exc

        if not content:
            raise GroqUnavailableError("Groq returned an empty response")
        return content

    @staticmethod
    def _parse(content: str) -> JobAnalysis:
        cleaned = re.sub(r"^```(?:json)?\s*", "", content.strip(), flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        payload: Any = json.loads(cleaned)
        return JobAnalysis.model_validate(payload)
