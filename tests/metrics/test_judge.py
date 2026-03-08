"""Tests for the blinded LLM-as-judge module."""

import json

from benchmark.metrics.judge import build_judge_prompt, parse_judge_response


class TestBuildJudgePrompt:
    """Tests for build_judge_prompt."""

    def test_judge_prompt_is_blinded(self) -> None:
        """Verify that 'CLI' and 'MCP' do NOT appear in the prompt,
        but 'Output A' and 'Output B' do."""
        prompt = build_judge_prompt(
            task_description="List files in the repo",
            output_a="file1.txt\nfile2.txt",
            output_b="file1.txt\nfile2.txt\nfile3.txt",
        )
        # The prompt must not reveal which system produced which output
        assert "CLI" not in prompt
        assert "MCP" not in prompt
        assert "cli" not in prompt
        assert "mcp" not in prompt
        assert "Output A" in prompt
        assert "Output B" in prompt

    def test_judge_prompt_includes_rubric(self) -> None:
        """Verify the prompt mentions the 1-5 scoring scale and evaluation criteria."""
        prompt = build_judge_prompt(
            task_description="Summarize the code",
            output_a="summary one",
            output_b="summary two",
        )
        assert "1" in prompt
        assert "5" in prompt
        assert "correctness" in prompt.lower()
        assert "completeness" in prompt.lower()


class TestParseJudgeResponse:
    """Tests for parse_judge_response."""

    def test_parse_judge_response_valid(self) -> None:
        """Parse a valid JSON response with all required keys."""
        response = json.dumps({
            "score_a": 4,
            "score_b": 3,
            "rationale_a": "Good output",
            "rationale_b": "Decent output",
        })
        result = parse_judge_response(response)
        assert result is not None
        assert result["score_a"] == 4
        assert result["score_b"] == 3
        assert result["rationale_a"] == "Good output"
        assert result["rationale_b"] == "Decent output"

    def test_parse_judge_response_bad_json(self) -> None:
        """Returns None for unparseable text."""
        result = parse_judge_response("this is not json at all")
        assert result is None

    def test_parse_judge_response_missing_keys(self) -> None:
        """Returns None when required keys are missing."""
        response = json.dumps({
            "score_a": 4,
            "rationale_a": "Good",
        })
        result = parse_judge_response(response)
        assert result is None
