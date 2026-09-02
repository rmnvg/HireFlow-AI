from typing import Any

import httpx


class HunarServiceError(Exception):
    """Base exception for safe Hunar failure handling."""


class HunarValidationError(HunarServiceError):
    pass


class HunarAuthenticationError(HunarServiceError):
    pass


class HunarSubscriptionError(HunarServiceError):
    pass


class HunarNotFoundError(HunarServiceError):
    pass


class HunarFieldError(HunarServiceError):
    pass


class HunarRateLimitError(HunarServiceError):
    pass


class HunarTimeoutError(HunarServiceError):
    pass


class HunarProviderError(HunarServiceError):
    pass


class HunarVoiceService:
    def __init__(
        self,
        client: httpx.Client,
        api_key: str,
        base_url: str,
        timeout: httpx.Timeout,
    ) -> None:
        self._client = client
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def list_agents(self) -> Any:
        return self._request("GET", "/agents/")

    def get_agent(self, agent_id: str) -> dict[str, Any]:
        response = self._request("GET", f"/agents/{agent_id}/")
        if not isinstance(response, dict):
            raise HunarProviderError("Hunar returned invalid agent data")
        return response

    def create_call(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = self._request("POST", "/calls/", json=payload)
        if not isinstance(response, dict):
            raise HunarProviderError("Hunar returned invalid call data")
        return response

    def get_call(self, hunar_call_id: str) -> dict[str, Any]:
        response = self._request("GET", f"/calls/{hunar_call_id}/")
        if not isinstance(response, dict):
            raise HunarProviderError("Hunar returned invalid call data")
        return response

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        try:
            response = self._client.request(
                method,
                f"{self._base_url}{path}",
                headers={
                    "X-API-Key": self._api_key,
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                timeout=self._timeout,
                **kwargs,
            )
        except httpx.TimeoutException as exc:
            raise HunarTimeoutError("Hunar request timed out") from exc
        except httpx.RequestError as exc:
            raise HunarProviderError("Hunar request failed") from exc

        error_by_status: dict[int, type[HunarServiceError]] = {
            400: HunarValidationError,
            401: HunarAuthenticationError,
            402: HunarSubscriptionError,
            404: HunarNotFoundError,
            422: HunarFieldError,
            429: HunarRateLimitError,
        }
        error_type = error_by_status.get(response.status_code)
        if error_type is not None:
            raise error_type(f"Hunar returned HTTP {response.status_code}")
        if response.status_code >= 500 or response.is_error:
            raise HunarProviderError("Hunar provider failure")

        try:
            return response.json()
        except ValueError as exc:
            raise HunarProviderError("Hunar returned invalid JSON") from exc


def unwrap_hunar_data(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("data")
    if isinstance(data, dict):
        nested = data.get("call") or data.get("agent")
        if isinstance(nested, dict):
            return nested
        return data
    return payload


def extract_required_agent_variables(agent_payload: dict[str, Any]) -> list[str]:
    agent = unwrap_hunar_data(agent_payload)
    required_names: list[str] = []
    explicit_required_keys = (
        "required_variables",
        "required_custom_data",
        "required_custom_data_variables",
        "required_prompt_variables",
    )
    variable_definition_keys = (
        "variables",
        "custom_data_variables",
        "dynamic_variables",
        "prompt_variables",
    )

    def add_name(value: Any) -> None:
        if isinstance(value, str) and value.strip() and value.strip() not in required_names:
            required_names.append(value.strip())

    def read_definitions(value: Any, all_required: bool) -> None:
        if isinstance(value, str):
            if all_required:
                add_name(value)
            return
        if isinstance(value, dict):
            for key, definition in value.items():
                if all_required or definition is True:
                    add_name(key)
                elif isinstance(definition, dict) and definition.get("required") is True:
                    add_name(definition.get("name") or definition.get("key") or key)
            return
        if not isinstance(value, list):
            return
        for definition in value:
            if isinstance(definition, str):
                if all_required:
                    add_name(definition)
                continue
            if not isinstance(definition, dict):
                continue
            if all_required or definition.get("required") is True:
                add_name(
                    definition.get("name")
                    or definition.get("key")
                    or definition.get("variable")
                    or definition.get("variable_name")
                )

    for key in explicit_required_keys:
        read_definitions(agent.get(key), all_required=True)
    for key in variable_definition_keys:
        read_definitions(agent.get(key), all_required=False)
    return required_names


def get_hunar_call_id(payload: dict[str, Any]) -> str | None:
    data = unwrap_hunar_data(payload)
    for key in ("id", "call_id", "uuid"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None
