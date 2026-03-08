"""Tests for output verification logic."""

from benchmark.metrics.verifier import VerificationResult, verify_output
from benchmark.tasks.schema import VerificationConfig


def test_exact_match_pass():
    """Full match returns passed=True, score=1.0."""
    config = VerificationConfig(
        type="exact_match",
        ground_truth=[{"name": "Alice", "age": 30}],
    )
    result = verify_output('[{"name": "Alice", "age": 30}]', config)
    assert result.passed is True
    assert result.score == 1.0


def test_exact_match_partial():
    """Agent found 1 of 2 items -> passed=False, score=0.5."""
    config = VerificationConfig(
        type="exact_match",
        ground_truth=[{"name": "Alice"}, {"name": "Bob"}],
    )
    result = verify_output('[{"name": "Alice"}]', config)
    assert result.passed is False
    assert result.score == 0.5
    assert "1/2" in result.details


def test_contains_match():
    """All strings found -> passed=True."""
    config = VerificationConfig(
        type="contains",
        ground_truth=["hello", "world"],
    )
    result = verify_output("hello beautiful world", config)
    assert result.passed is True
    assert result.score == 1.0


def test_exact_match_with_unparseable_output():
    """Unparseable output returns passed=False, score=0.0."""
    config = VerificationConfig(
        type="exact_match",
        ground_truth=[{"key": "value"}],
    )
    result = verify_output("this is not json at all", config)
    assert result.passed is False
    assert result.score == 0.0


def test_llm_judge_deferred():
    """LLM judge type returns passed=True (deferred)."""
    config = VerificationConfig(
        type="llm_judge",
        judge_prompt="Is this good?",
    )
    result = verify_output("some output", config)
    assert result.passed is True
    assert result.score == 1.0
    assert "Deferred" in result.details


def test_exact_match_json_embedded_in_text():
    """JSON buried in explanation text is still extracted."""
    config = VerificationConfig(
        type="exact_match",
        ground_truth=[{"status": "ok"}],
    )
    output = 'Here is the result: [{"status": "ok"}] as you can see.'
    result = verify_output(output, config)
    assert result.passed is True
    assert result.score == 1.0
