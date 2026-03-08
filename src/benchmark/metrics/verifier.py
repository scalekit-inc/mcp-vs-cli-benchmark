import json
import re
from dataclasses import dataclass
from typing import Any

from benchmark.tasks.schema import VerificationConfig


@dataclass
class VerificationResult:
    passed: bool
    score: float  # 0.0 to 1.0
    details: str


def verify_output(agent_output: str, config: VerificationConfig) -> VerificationResult:
    """Verify agent output against ground truth."""
    if config.type == "exact_match":
        return _exact_match(agent_output, config.ground_truth)
    elif config.type == "contains":
        return _contains_match(agent_output, config.ground_truth)
    elif config.type == "llm_judge":
        return VerificationResult(passed=True, score=1.0, details="Deferred to LLM judge")
    elif config.type == "api_check":
        return VerificationResult(passed=True, score=1.0, details="Deferred to API check")
    else:
        return VerificationResult(passed=False, score=0.0, details=f"Unknown type: {config.type}")


def _extract_json(text: str) -> Any:
    """Try to extract JSON from agent output text."""
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass
    for pattern in [r'\[.*\]', r'\{.*\}']:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                continue
    return None


def _exact_match(agent_output: str, ground_truth: Any) -> VerificationResult:
    if not isinstance(ground_truth, list):
        ground_truth = [ground_truth]
    parsed = _extract_json(agent_output)
    if parsed is None:
        return VerificationResult(passed=False, score=0.0, details="Could not parse agent output as JSON")
    if not isinstance(parsed, list):
        parsed = [parsed]
    matched = 0
    for expected in ground_truth:
        for actual in parsed:
            if _items_match(expected, actual):
                matched += 1
                break
    total = len(ground_truth)
    score = matched / total if total > 0 else 0.0
    return VerificationResult(passed=matched == total, score=score, details=f"Matched {matched}/{total} items")


def _items_match(expected: Any, actual: Any) -> bool:
    if isinstance(expected, dict) and isinstance(actual, dict):
        return all(key in actual and actual[key] == value for key, value in expected.items())
    return expected == actual


def _contains_match(agent_output: str, ground_truth: Any) -> VerificationResult:
    if not isinstance(ground_truth, list):
        ground_truth = [ground_truth]
    matched = sum(1 for item in ground_truth if str(item) in agent_output)
    total = len(ground_truth)
    score = matched / total if total > 0 else 0.0
    return VerificationResult(passed=matched == total, score=score, details=f"Found {matched}/{total} expected strings")
