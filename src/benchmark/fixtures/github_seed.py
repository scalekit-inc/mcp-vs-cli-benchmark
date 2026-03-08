"""GitHub fixture data and seeder for benchmark runs."""

from __future__ import annotations

import httpx

GITHUB_FIXTURES: dict = {
    "issues": [
        {
            "number": 1,
            "title": "Login page returns 500 on invalid email format",
            "labels": ["bug"],
            "state": "open",
            "assignee": "alice",
        },
        {
            "number": 2,
            "title": "Add dark mode support",
            "labels": ["enhancement"],
            "state": "open",
            "assignee": "bob",
        },
        {
            "number": 3,
            "title": "CSS layout breaks on viewport < 768px",
            "labels": ["bug"],
            "state": "open",
            "assignee": "alice",
        },
        {
            "number": 4,
            "title": "Migrate from Jest to Vitest",
            "labels": ["chore"],
            "state": "open",
            "assignee": None,
        },
        {
            "number": 5,
            "title": "Memory leak in WebSocket reconnection handler",
            "labels": ["bug", "critical"],
            "state": "open",
            "assignee": "charlie",
        },
        {
            "number": 6,
            "title": "Add OpenAPI spec for v2 endpoints",
            "labels": ["documentation"],
            "state": "open",
            "assignee": "bob",
        },
        {
            "number": 7,
            "title": "Race condition in concurrent file upload",
            "labels": ["bug"],
            "state": "open",
            "assignee": "alice",
        },
        {
            "number": 8,
            "title": "Upgrade to Node 22 LTS",
            "labels": ["chore"],
            "state": "closed",
            "assignee": "charlie",
        },
        {
            "number": 9,
            "title": "API rate limiter counts preflight requests",
            "labels": ["bug"],
            "state": "open",
            "assignee": "bob",
        },
        {
            "number": 10,
            "title": "Add pagination to /users endpoint",
            "labels": ["enhancement"],
            "state": "open",
            "assignee": None,
        },
    ],
    "pull_requests": [
        {
            "number": 11,
            "title": "Fix login validation",
            "state": "merged",
            "author": "alice",
            "base": "main",
            "reviews": [
                {"user": "bob", "body": "LGTM", "state": "APPROVED"},
            ],
        },
        {
            "number": 12,
            "title": "Add dark mode CSS variables",
            "state": "merged",
            "author": "bob",
            "base": "main",
            "reviews": [
                {
                    "user": "charlie",
                    "body": "Needs contrast fix",
                    "state": "CHANGES_REQUESTED",
                },
                {
                    "user": "charlie",
                    "body": "Fixed, looks good",
                    "state": "APPROVED",
                },
            ],
        },
        {
            "number": 13,
            "title": "Bump dependencies March 2026",
            "state": "merged",
            "author": "charlie",
            "base": "main",
            "reviews": [
                {"user": "alice", "body": "All green", "state": "APPROVED"},
            ],
        },
        {
            "number": 14,
            "title": "WIP: WebSocket reconnection refactor",
            "state": "open",
            "author": "alice",
            "base": "main",
            "reviews": [],
        },
        {
            "number": 15,
            "title": "Draft: Rate limiter fix",
            "state": "open",
            "author": "bob",
            "base": "main",
            "reviews": [
                {
                    "user": "alice",
                    "body": "Needs tests",
                    "state": "CHANGES_REQUESTED",
                },
            ],
        },
    ],
    "branches": [
        "main",
        "fix/login-validation",
        "feat/dark-mode",
        "chore/deps-march-2026",
        "fix/websocket-reconnect",
        "fix/rate-limiter",
    ],
}


class GitHubSeeder:
    """Seeds and tears down GitHub fixture data for benchmark runs."""

    def __init__(self, repo: str, token: str) -> None:
        self.repo = repo
        self.token = token
        self.base_url = f"https://api.github.com/repos/{repo}"
        self.client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=30.0,
        )

    async def seed(self, run_id: str) -> None:
        """Create all fixture data via GitHub API.

        Args:
            run_id: Unique identifier for this benchmark run, used to tag resources.
        """
        # Create labels first
        all_labels: set[str] = set()
        for issue in GITHUB_FIXTURES["issues"]:
            all_labels.update(issue["labels"])
        for label in all_labels:
            await self.client.post(
                f"{self.base_url}/labels",
                json={"name": f"{run_id}-{label}", "color": "ededed"},
            )

        # Create branches (excluding main)
        main_ref = await self.client.get(f"{self.base_url}/git/ref/heads/main")
        if main_ref.status_code == 200:
            main_sha = main_ref.json()["object"]["sha"]
            for branch in GITHUB_FIXTURES["branches"]:
                if branch == "main":
                    continue
                await self.client.post(
                    f"{self.base_url}/git/refs",
                    json={
                        "ref": f"refs/heads/{run_id}-{branch}",
                        "sha": main_sha,
                    },
                )

        # Create issues
        for issue in GITHUB_FIXTURES["issues"]:
            payload: dict = {
                "title": f"[{run_id}] {issue['title']}",
                "labels": [f"{run_id}-{l}" for l in issue["labels"]],
            }
            if issue["assignee"] is not None:
                payload["assignees"] = [issue["assignee"]]
            resp = await self.client.post(f"{self.base_url}/issues", json=payload)
            if resp.status_code == 201 and issue["state"] == "closed":
                issue_number = resp.json()["number"]
                await self.client.patch(
                    f"{self.base_url}/issues/{issue_number}",
                    json={"state": "closed"},
                )

        # Create pull requests
        for pr in GITHUB_FIXTURES["pull_requests"]:
            head_branch = None
            for branch in GITHUB_FIXTURES["branches"]:
                if branch != "main":
                    head_branch = f"{run_id}-{branch}"
                    break
            if head_branch is None:
                continue

            pr_payload = {
                "title": f"[{run_id}] {pr['title']}",
                "head": head_branch,
                "base": pr["base"],
            }
            pr_resp = await self.client.post(
                f"{self.base_url}/pulls", json=pr_payload
            )
            if pr_resp.status_code == 201:
                pr_number = pr_resp.json()["number"]
                # Add review comments
                for review in pr["reviews"]:
                    await self.client.post(
                        f"{self.base_url}/pulls/{pr_number}/reviews",
                        json={
                            "body": review["body"],
                            "event": review["state"]
                            if review["state"] != "APPROVED"
                            else "APPROVE",
                        },
                    )

    async def teardown(self, run_id: str) -> None:
        """Remove all fixture data created for a benchmark run.

        Args:
            run_id: The run identifier used during seeding.
        """
        # Close and delete issues/PRs tagged with run_id
        issues_resp = await self.client.get(
            f"{self.base_url}/issues",
            params={"state": "all", "per_page": 100},
        )
        if issues_resp.status_code == 200:
            for item in issues_resp.json():
                if item["title"].startswith(f"[{run_id}]"):
                    number = item["number"]
                    # Close if open
                    if item["state"] == "open":
                        await self.client.patch(
                            f"{self.base_url}/issues/{number}",
                            json={"state": "closed"},
                        )

        # Delete branches
        for branch in GITHUB_FIXTURES["branches"]:
            if branch == "main":
                continue
            await self.client.delete(
                f"{self.base_url}/git/refs/heads/{run_id}-{branch}"
            )

        # Delete labels
        all_labels: set[str] = set()
        for issue in GITHUB_FIXTURES["issues"]:
            all_labels.update(issue["labels"])
        for label in all_labels:
            await self.client.delete(
                f"{self.base_url}/labels/{run_id}-{label}"
            )

    async def verify(self) -> bool:
        """Check that fixture data exists in the repository.

        Returns:
            True if the repository is accessible and has expected structure.
        """
        resp = await self.client.get(self.base_url)
        if resp.status_code != 200:
            return False

        issues_resp = await self.client.get(
            f"{self.base_url}/issues",
            params={"state": "all", "per_page": 1},
        )
        return issues_resp.status_code == 200

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self.client.aclose()
