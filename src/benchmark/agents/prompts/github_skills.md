# gh CLI Skills

`gh` is pre-authenticated. Use it directly -- no login needed.

## Repository Info
```bash
gh repo view {owner}/{repo} --json name,description,language,licenseInfo,defaultBranchRef
```

## Issues
```bash
# List issues
gh issue list -R {owner}/{repo} --json number,title,state,labels --limit 100
# Filter by state
gh issue list -R {owner}/{repo} --state closed --json number,title,state,labels --limit 50
# View single issue
gh issue view {number} -R {owner}/{repo} --json number,title,body,state,labels,comments
```

## Pull Requests
```bash
# List PRs (default: open)
gh pr list -R {owner}/{repo} --json number,title,state,author,mergedAt --limit 100
# Merged PRs by author
gh pr list -R {owner}/{repo} --state merged --author {user} --json number,title,mergedAt --limit 50
# View single PR with reviews
gh pr view {number} -R {owner}/{repo} --json number,title,state,author,reviews,files,additions,deletions
```

## File Contents
```bash
gh api repos/{owner}/{repo}/contents/{path} -q '.content' | base64 -d
# Directory listing
gh api repos/{owner}/{repo}/contents/{path} -q '.[].name'
```

## Releases
```bash
gh release list -R {owner}/{repo} --json tagName,name,publishedAt --limit 5
```

## Search
```bash
gh search issues --repo {owner}/{repo} --match title "keyword"
gh search repos "query" --json fullName,description,stargazersCount --limit 10
```

## API (raw REST calls)
```bash
gh api repos/{owner}/{repo}/contributors -q '.[].login'
gh api repos/{owner}/{repo}/commits --jq '.[0:5] | .[].commit.message'
```

## Key Tips
- Always use `--json` for structured output (never parse human-readable tables)
- Use `-q` / `--jq` to extract specific fields from JSON
- Use `-R owner/repo` to target a repository
- Pipe to `jq` for complex transformations: `gh ... --json foo | jq '.[] | select(.state=="open")'`
- Combine `--limit` with `--json` to control result count
