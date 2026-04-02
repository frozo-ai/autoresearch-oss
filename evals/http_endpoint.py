"""HTTP endpoint eval adapter — calls an HTTP endpoint and parses the score from JSON."""

import json
import logging
from pathlib import Path

import httpx

from evals.base import EvalAdapter, EvalResult

logger = logging.getLogger(__name__)


class HttpEndpointAdapter(EvalAdapter):
    """Eval by calling an HTTP endpoint.

    Config:
        endpoint_url: URL to POST to
        auth_header: Optional auth header value
        score_path: JSON path to score in response (e.g. "result.score")
        payload_file: File to send as the request body (optional)
    """

    def run(self, workspace: Path, metric_name: str) -> EvalResult:
        endpoint_url = self.config.get("endpoint_url")
        if not endpoint_url:
            return EvalResult(
                metric_name=metric_name,
                score=0.0,
                success=False,
                error_message="endpoint_url is required for HTTP eval",
            )

        auth_header = self.config.get("auth_header", "")
        score_path = self.config.get("score_path", "score")
        payload_file = self.config.get("payload_file")

        headers = {"Content-Type": "application/json"}
        if auth_header:
            headers["Authorization"] = auth_header

        # Build payload
        payload = {}
        if payload_file:
            payload_path = workspace / payload_file
            if payload_path.exists():
                payload = {"content": payload_path.read_text()}

        try:
            with httpx.Client(timeout=self.time_budget) as client:
                response = client.post(endpoint_url, json=payload, headers=headers)
                response.raise_for_status()
        except httpx.TimeoutException:
            return EvalResult(
                metric_name=metric_name,
                score=0.0,
                success=False,
                error_message=f"HTTP eval timed out after {self.time_budget}s",
            )
        except httpx.HTTPStatusError as e:
            return EvalResult(
                metric_name=metric_name,
                score=0.0,
                success=False,
                error_message=f"HTTP eval failed ({e.response.status_code}): {e.response.text[:500]}",
            )

        try:
            data = response.json()
        except json.JSONDecodeError:
            return EvalResult(
                metric_name=metric_name,
                score=0.0,
                success=False,
                error_message="HTTP eval: response is not valid JSON",
                raw_output=response.text[:1000],
            )

        # Navigate score_path (e.g. "result.score")
        value = data
        for key in score_path.split("."):
            if isinstance(value, dict):
                value = value.get(key)
            else:
                value = None
                break

        if value is None:
            return EvalResult(
                metric_name=metric_name,
                score=0.0,
                success=False,
                error_message=f"Score not found at path '{score_path}' in response",
                raw_output=json.dumps(data, indent=2),
            )

        try:
            score = float(value)
        except (TypeError, ValueError):
            return EvalResult(
                metric_name=metric_name,
                score=0.0,
                success=False,
                error_message=f"Score at '{score_path}' is not a number: {value}",
            )

        return EvalResult(
            metric_name=metric_name,
            score=score,
            success=True,
            raw_output=json.dumps(data, indent=2),
        )
