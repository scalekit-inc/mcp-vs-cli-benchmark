# MCP vs CLI Benchmark Report

**Total runs:** 68
**Tasks:** 5
**Modalities:** CLI, CLI+Skills, MCP
**Model:** claude-sonnet-4-20250514

## Get repository language and license (`github_01`)

CLI: 5 | CLI+Skills: 5 | MCP: 3

| Metric | CLI | CLI+Skills | MCP |
|--------|--------|--------|--------|
| total_tokens | 1365.0 | 4724.0 | 44026.0 |
| tool_calls | 1.0 | 2.0 | 2.0 |
| wall_clock | 4.0 | 6.0 | 11.0 |
| completion | 1.0 | 1.0 | 1.0 |

## Get PR details including review status (`github_02`)

CLI: 5 | CLI+Skills: 5 | MCP: 3

| Metric | CLI | CLI+Skills | MCP |
|--------|--------|--------|--------|
| total_tokens | 1648.0 | 2816.0 | 32279.0 |
| tool_calls | 1.0 | 1.0 | 2.0 |
| wall_clock | 7.8 | 4.7 | 8.5 |
| completion | 1.0 | 1.0 | 1.0 |

## Get repository metadata and installation instructions (`github_03`)

CLI: 5 | CLI+Skills: 5 | MCP: 5

| Metric | CLI | CLI+Skills | MCP |
|--------|--------|--------|--------|
| total_tokens | 9386.0 | 12210.0 | 82835.0 |
| tool_calls | 6.0 | 4.0 | 4.0 |
| wall_clock | 26.0 | 13.5 | 18.6 |
| completion | 1.0 | 1.0 | 1.0 |

## Find and summarize merged PRs by contributor (`github_04`)

CLI: 5 | CLI+Skills: 5 | MCP: 3

| Metric | CLI | CLI+Skills | MCP |
|--------|--------|--------|--------|
| total_tokens | 5010.0 | 6107.0 | 33712.0 |
| tool_calls | 1.0 | 1.0 | 1.0 |
| wall_clock | 18.9 | 16.4 | 18.7 |
| completion | 1.0 | 1.0 | 1.0 |

## Find latest release and list key dependencies (`github_05`)

CLI: 5 | CLI+Skills: 5 | MCP: 4

| Metric | CLI | CLI+Skills | MCP |
|--------|--------|--------|--------|
| total_tokens | 8750.0 | 6860.0 | 37402.0 |
| tool_calls | 3.0 | 2.0 | 2.0 |
| wall_clock | 15.1 | 12.3 | 13.7 |
| completion | 1.0 | 1.0 | 1.0 |

## Pairwise Comparisons

### CLI vs CLI+Skills

| Task | Metric | CLI (median) | CLI+Skills (median) | Diff (mean) | p-value | Cohen's d | Winner |
|------|--------|-------------|-------------|-------------|---------|-----------|--------|
| github_01 | total_tokens | 1365.0 | 4724.0 | -3359.0 | 0.0040 | 0.00 | CLI |
| github_01 | tool_calls | 1.0 | 2.0 | -1.0 | 0.0040 | 0.00 | CLI |
| github_01 | wall_clock | 4.0 | 6.0 | -2.2 | 0.0317 | -1.71 | CLI |
| github_02 | total_tokens | 1648.0 | 2816.0 | -1171.6 | 0.0056 | -205.83 | CLI |
| github_02 | tool_calls | 1.0 | 1.0 | +0.0 | n/a | 0.00 | tie |
| github_02 | wall_clock | 7.8 | 4.7 | +1.2 | 0.4206 | 0.67 | tie |
| github_03 | total_tokens | 9386.0 | 12210.0 | -1370.8 | 0.1264 | -0.61 | tie |
| github_03 | tool_calls | 6.0 | 4.0 | +2.4 | 0.0056 | 3.79 | CLI+Skills |
| github_03 | wall_clock | 26.0 | 13.5 | +15.6 | 0.0159 | 1.84 | CLI+Skills |
| github_04 | total_tokens | 5010.0 | 6107.0 | +2005.6 | 0.1376 | 0.41 | tie |
| github_04 | tool_calls | 1.0 | 1.0 | +0.6 | 0.4237 | 0.63 | tie |
| github_04 | wall_clock | 18.9 | 16.4 | +19.5 | 0.2222 | 0.68 | tie |
| github_05 | total_tokens | 8750.0 | 6860.0 | +1587.2 | 0.0056 | 3.32 | CLI+Skills |
| github_05 | tool_calls | 3.0 | 2.0 | +0.8 | 0.0200 | 2.53 | CLI+Skills |
| github_05 | wall_clock | 15.1 | 12.3 | -6.9 | 1.0000 | -0.55 | tie |

### CLI vs MCP

| Task | Metric | CLI (median) | MCP (median) | Diff (mean) | p-value | Cohen's d | Winner |
|------|--------|-------------|-------------|-------------|---------|-----------|--------|
| github_01 | total_tokens | 1365.0 | 44026.0 | -42661.0 | 0.0135 | 0.00 | CLI |
| github_01 | tool_calls | 1.0 | 2.0 | -1.0 | 0.0135 | 0.00 | CLI |
| github_01 | wall_clock | 4.0 | 11.0 | -6.4 | 0.0357 | -6.25 | CLI |
| github_02 | total_tokens | 1648.0 | 32279.0 | -30631.0 | 0.0135 | 0.00 | CLI |
| github_02 | tool_calls | 1.0 | 2.0 | -1.0 | 0.0135 | 0.00 | CLI |
| github_02 | wall_clock | 7.8 | 8.5 | -3.4 | 0.2500 | -1.34 | tie |
| github_03 | total_tokens | 9386.0 | 82835.0 | -72018.6 | 0.0056 | -31.84 | CLI |
| github_03 | tool_calls | 6.0 | 4.0 | +2.4 | 0.0056 | 3.79 | MCP |
| github_03 | wall_clock | 26.0 | 18.6 | +10.0 | 0.0952 | 1.15 | tie |
| github_04 | total_tokens | 5010.0 | 33712.0 | -25590.2 | 0.0325 | -4.52 | CLI |
| github_04 | tool_calls | 1.0 | 1.0 | +0.6 | 0.6056 | 0.55 | tie |
| github_04 | wall_clock | 18.9 | 18.7 | +15.4 | 1.0000 | 0.47 | tie |
| github_05 | total_tokens | 8750.0 | 37402.0 | -28652.0 | 0.0072 | 0.00 | CLI |
| github_05 | tool_calls | 3.0 | 2.0 | +1.0 | 0.0072 | 0.00 | MCP |
| github_05 | wall_clock | 15.1 | 13.7 | -0.4 | 0.9048 | -0.11 | tie |

### CLI+Skills vs MCP

| Task | Metric | CLI+Skills (median) | MCP (median) | Diff (mean) | p-value | Cohen's d | Winner |
|------|--------|-------------|-------------|-------------|---------|-----------|--------|
| github_01 | total_tokens | 4724.0 | 44026.0 | -39302.0 | 0.0135 | 0.00 | CLI+Skills |
| github_01 | tool_calls | 2.0 | 2.0 | +0.0 | n/a | 0.00 | tie |
| github_01 | wall_clock | 6.0 | 11.0 | -4.2 | 0.0357 | -3.49 | CLI+Skills |
| github_02 | total_tokens | 2816.0 | 32279.0 | -29459.4 | 0.0222 | -4482.10 | CLI+Skills |
| github_02 | tool_calls | 1.0 | 2.0 | -1.0 | 0.0135 | 0.00 | CLI+Skills |
| github_02 | wall_clock | 4.7 | 8.5 | -4.6 | 0.0357 | -2.08 | CLI+Skills |
| github_03 | total_tokens | 12210.0 | 82835.0 | -70647.8 | 0.0067 | -1981.37 | CLI+Skills |
| github_03 | tool_calls | 4.0 | 4.0 | +0.0 | n/a | 0.00 | tie |
| github_03 | wall_clock | 13.5 | 18.6 | -5.7 | 0.0317 | -1.93 | CLI+Skills |
| github_04 | total_tokens | 6107.0 | 33712.0 | -27595.8 | 0.0358 | -863.72 | CLI+Skills |
| github_04 | tool_calls | 1.0 | 1.0 | +0.0 | n/a | 0.00 | tie |
| github_04 | wall_clock | 16.4 | 18.7 | -4.1 | 0.2500 | -1.37 | tie |
| github_05 | total_tokens | 6860.0 | 37402.0 | -30239.2 | 0.0108 | -59.08 | CLI+Skills |
| github_05 | tool_calls | 2.0 | 2.0 | +0.2 | 0.5023 | 0.59 | tie |
| github_05 | wall_clock | 12.3 | 13.7 | +6.5 | 0.9048 | 0.48 | tie |

## Summary

- **CLI** wins: 12
- **CLI+Skills** wins: 13
- **MCP** wins: 2
- Ties: 18
