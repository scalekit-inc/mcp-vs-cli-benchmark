"""Tests for GitHub fixture data and GitHubSeeder."""

from benchmark.fixtures.github_seed import GITHUB_FIXTURES, GitHubSeeder


class TestGitHubFixtureData:
    """Verify fixture data structure and consistency."""

    def test_github_fixture_data_is_consistent(self) -> None:
        """Verify 10 issues, 5 PRs, 5 bug issues, 3 merged + 2 open PRs."""
        issues = GITHUB_FIXTURES["issues"]
        prs = GITHUB_FIXTURES["pull_requests"]
        branches = GITHUB_FIXTURES["branches"]

        # Counts
        assert len(issues) == 10
        assert len(prs) == 5
        assert len(branches) == 6

        # 5 issues with "bug" label
        bug_issues = [i for i in issues if "bug" in i["labels"]]
        assert len(bug_issues) == 5

        # 3 merged + 2 open PRs
        merged_prs = [p for p in prs if p["state"] == "merged"]
        open_prs = [p for p in prs if p["state"] == "open"]
        assert len(merged_prs) == 3
        assert len(open_prs) == 2

    def test_seed_and_teardown_are_callable(self) -> None:
        """Verify GitHubSeeder has seed/teardown/verify methods."""
        seeder = GitHubSeeder(repo="owner/repo", token="fake-token")

        assert callable(getattr(seeder, "seed", None))
        assert callable(getattr(seeder, "teardown", None))
        assert callable(getattr(seeder, "verify", None))
        assert callable(getattr(seeder, "close", None))
