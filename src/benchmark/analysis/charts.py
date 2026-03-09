"""Visualization module for benchmark results using Plotly."""

from collections import defaultdict
from pathlib import Path

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from benchmark.metrics.schemas import RunResult

# Style constants
CLI_COLOR = "#3b82f6"
MCP_COLOR = "#d946ef"
BACKGROUND_COLOR = "white"
GRID_COLOR = "#e5e7eb"

_LAYOUT_DEFAULTS = dict(
    plot_bgcolor=BACKGROUND_COLOR,
    paper_bgcolor=BACKGROUND_COLOR,
    font=dict(family="Inter, system-ui, sans-serif", size=12, color="#1f2937"),
    xaxis=dict(gridcolor=GRID_COLOR),
    yaxis=dict(gridcolor=GRID_COLOR),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
)


def _group_by_task_and_modality(
    results: list[RunResult],
) -> dict[str, dict[str, list[RunResult]]]:
    """Group results by task_id then modality."""
    grouped: dict[str, dict[str, list[RunResult]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for r in results:
        grouped[r.task_id][r.modality].append(r)
    return dict(grouped)


def _sorted_task_ids(grouped: dict[str, dict[str, list[RunResult]]]) -> list[str]:
    return sorted(grouped.keys())


def token_comparison_chart(results: list[RunResult]) -> go.Figure:
    """Grouped bar chart comparing median total tokens (CLI vs MCP) per task.

    Includes error bars showing the p25-p75 interquartile range.
    """
    grouped = _group_by_task_and_modality(results)
    task_ids = _sorted_task_ids(grouped)

    cli_medians, mcp_medians = [], []
    cli_err_minus, cli_err_plus = [], []
    mcp_err_minus, mcp_err_plus = [], []

    for tid in task_ids:
        for modality, medians, err_m, err_p in [
            ("cli", cli_medians, cli_err_minus, cli_err_plus),
            ("mcp", mcp_medians, mcp_err_minus, mcp_err_plus),
        ]:
            runs = grouped[tid].get(modality, [])
            if runs:
                vals = [r.total_tokens for r in runs]
                med = float(np.median(vals))
                p25 = float(np.percentile(vals, 25))
                p75 = float(np.percentile(vals, 75))
                medians.append(med)
                err_m.append(max(med - p25, 0))
                err_p.append(max(p75 - med, 0))
            else:
                medians.append(0)
                err_m.append(0)
                err_p.append(0)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="CLI",
        x=task_ids,
        y=cli_medians,
        marker_color=CLI_COLOR,
        error_y=dict(type="data", symmetric=False, array=cli_err_plus, arrayminus=cli_err_minus),
    ))
    fig.add_trace(go.Bar(
        name="MCP",
        x=task_ids,
        y=mcp_medians,
        marker_color=MCP_COLOR,
        error_y=dict(type="data", symmetric=False, array=mcp_err_plus, arrayminus=mcp_err_minus),
    ))
    fig.update_layout(
        title="Token Usage Comparison (Median with IQR)",
        xaxis_title="Task",
        yaxis_title="Total Tokens",
        barmode="group",
        **_LAYOUT_DEFAULTS,
    )
    return fig


def latency_box_plot(results: list[RunResult]) -> go.Figure:
    """Box plot of wall_clock_seconds for CLI vs MCP, grouped by task."""
    grouped = _group_by_task_and_modality(results)
    task_ids = _sorted_task_ids(grouped)

    fig = go.Figure()
    for modality, color, name in [("cli", CLI_COLOR, "CLI"), ("mcp", MCP_COLOR, "MCP")]:
        x_vals: list[str] = []
        y_vals: list[float] = []
        for tid in task_ids:
            runs = grouped[tid].get(modality, [])
            for r in runs:
                x_vals.append(tid)
                y_vals.append(r.wall_clock_seconds)
        fig.add_trace(go.Box(
            name=name,
            x=x_vals,
            y=y_vals,
            marker_color=color,
            boxmean=True,
        ))

    fig.update_layout(
        title="Latency Distribution by Task",
        xaxis_title="Task",
        yaxis_title="Wall Clock (seconds)",
        boxmode="group",
        **_LAYOUT_DEFAULTS,
    )
    return fig


def tool_calls_chart(results: list[RunResult]) -> go.Figure:
    """Grouped bar chart comparing median tool call counts (CLI vs MCP) per task.

    Includes error bars showing the p25-p75 interquartile range.
    """
    grouped = _group_by_task_and_modality(results)
    task_ids = _sorted_task_ids(grouped)

    cli_medians, mcp_medians = [], []
    cli_err_minus, cli_err_plus = [], []
    mcp_err_minus, mcp_err_plus = [], []

    for tid in task_ids:
        for modality, medians, err_m, err_p in [
            ("cli", cli_medians, cli_err_minus, cli_err_plus),
            ("mcp", mcp_medians, mcp_err_minus, mcp_err_plus),
        ]:
            runs = grouped[tid].get(modality, [])
            if runs:
                vals = [r.tool_call_count for r in runs]
                med = float(np.median(vals))
                p25 = float(np.percentile(vals, 25))
                p75 = float(np.percentile(vals, 75))
                medians.append(med)
                err_m.append(max(med - p25, 0))
                err_p.append(max(p75 - med, 0))
            else:
                medians.append(0)
                err_m.append(0)
                err_p.append(0)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="CLI",
        x=task_ids,
        y=cli_medians,
        marker_color=CLI_COLOR,
        error_y=dict(type="data", symmetric=False, array=cli_err_plus, arrayminus=cli_err_minus),
    ))
    fig.add_trace(go.Bar(
        name="MCP",
        x=task_ids,
        y=mcp_medians,
        marker_color=MCP_COLOR,
        error_y=dict(type="data", symmetric=False, array=mcp_err_plus, arrayminus=mcp_err_minus),
    ))
    fig.update_layout(
        title="Tool Call Count Comparison (Median with IQR)",
        xaxis_title="Task",
        yaxis_title="Tool Calls",
        barmode="group",
        **_LAYOUT_DEFAULTS,
    )
    return fig


def completion_rate_chart(results: list[RunResult]) -> go.Figure:
    """Grouped bar chart showing completion rates (%) per task per modality."""
    grouped = _group_by_task_and_modality(results)
    task_ids = _sorted_task_ids(grouped)

    cli_rates, mcp_rates = [], []
    for tid in task_ids:
        for modality, rates in [("cli", cli_rates), ("mcp", mcp_rates)]:
            runs = grouped[tid].get(modality, [])
            if runs:
                rate = sum(1 for r in runs if r.task_completed) / len(runs) * 100
                rates.append(rate)
            else:
                rates.append(0)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="CLI",
        x=task_ids,
        y=cli_rates,
        marker_color=CLI_COLOR,
    ))
    fig.add_trace(go.Bar(
        name="MCP",
        x=task_ids,
        y=mcp_rates,
        marker_color=MCP_COLOR,
    ))
    fig.update_layout(
        title="Task Completion Rate",
        xaxis_title="Task",
        yaxis_title="Completion Rate (%)",
        yaxis_range=[0, 105],
        barmode="group",
        **_LAYOUT_DEFAULTS,
    )
    return fig


def save_charts(results: list[RunResult], output_dir: Path) -> list[Path]:
    """Generate all charts and save as individual HTML files.

    Returns list of saved file paths.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    chart_funcs = [
        ("token_comparison", token_comparison_chart),
        ("latency_box_plot", latency_box_plot),
        ("tool_calls", tool_calls_chart),
        ("completion_rate", completion_rate_chart),
    ]

    paths: list[Path] = []
    for name, func in chart_funcs:
        fig = func(results)
        path = output_dir / f"{name}.html"
        fig.write_html(str(path), include_plotlyjs="cdn")
        paths.append(path)

    return paths


def generate_summary_dashboard(results: list[RunResult], output_dir: Path) -> Path:
    """Generate a single HTML dashboard with all charts as subplots.

    Returns the path to the saved HTML file.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    grouped = _group_by_task_and_modality(results)
    task_ids = _sorted_task_ids(grouped)

    fig = make_subplots(
        rows=2,
        cols=2,
        subplot_titles=(
            "Token Usage (Median)",
            "Latency Distribution",
            "Tool Call Count (Median)",
            "Completion Rate (%)",
        ),
        horizontal_spacing=0.1,
        vertical_spacing=0.12,
    )

    # --- Token comparison (row=1, col=1) ---
    for modality, color, name in [("cli", CLI_COLOR, "CLI"), ("mcp", MCP_COLOR, "MCP")]:
        medians = []
        for tid in task_ids:
            runs = grouped[tid].get(modality, [])
            medians.append(float(np.median([r.total_tokens for r in runs])) if runs else 0)
        fig.add_trace(
            go.Bar(name=name, x=task_ids, y=medians, marker_color=color, showlegend=True),
            row=1, col=1,
        )

    # --- Latency box plot (row=1, col=2) ---
    for modality, color, name in [("cli", CLI_COLOR, "CLI"), ("mcp", MCP_COLOR, "MCP")]:
        x_vals, y_vals = [], []
        for tid in task_ids:
            for r in grouped[tid].get(modality, []):
                x_vals.append(tid)
                y_vals.append(r.wall_clock_seconds)
        fig.add_trace(
            go.Box(name=name, x=x_vals, y=y_vals, marker_color=color, showlegend=False),
            row=1, col=2,
        )

    # --- Tool calls (row=2, col=1) ---
    for modality, color, name in [("cli", CLI_COLOR, "CLI"), ("mcp", MCP_COLOR, "MCP")]:
        medians = []
        for tid in task_ids:
            runs = grouped[tid].get(modality, [])
            medians.append(float(np.median([r.tool_call_count for r in runs])) if runs else 0)
        fig.add_trace(
            go.Bar(name=name, x=task_ids, y=medians, marker_color=color, showlegend=False),
            row=2, col=1,
        )

    # --- Completion rate (row=2, col=2) ---
    for modality, color, name in [("cli", CLI_COLOR, "CLI"), ("mcp", MCP_COLOR, "MCP")]:
        rates = []
        for tid in task_ids:
            runs = grouped[tid].get(modality, [])
            rates.append(sum(1 for r in runs if r.task_completed) / len(runs) * 100 if runs else 0)
        fig.add_trace(
            go.Bar(name=name, x=task_ids, y=rates, marker_color=color, showlegend=False),
            row=2, col=2,
        )

    fig.update_layout(
        title_text="MCP vs CLI Benchmark Dashboard",
        height=800,
        plot_bgcolor=BACKGROUND_COLOR,
        paper_bgcolor=BACKGROUND_COLOR,
        font=dict(family="Inter, system-ui, sans-serif", size=12, color="#1f2937"),
        legend=dict(orientation="h", yanchor="bottom", y=1.06, xanchor="right", x=1),
        barmode="group",
    )

    # Style all axes
    for i in range(1, 5):
        fig.update_xaxes(gridcolor=GRID_COLOR, row=(i - 1) // 2 + 1, col=(i - 1) % 2 + 1)
        fig.update_yaxes(gridcolor=GRID_COLOR, row=(i - 1) // 2 + 1, col=(i - 1) % 2 + 1)

    path = output_dir / "dashboard.html"
    fig.write_html(str(path), include_plotlyjs="cdn")
    return path
