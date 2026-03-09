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
GATEWAY_COLOR = "#10b981"
CLI_SKILLED_COLOR = "#f59e0b"
BACKGROUND_COLOR = "white"
GRID_COLOR = "#e5e7eb"

MODALITY_COLORS: dict[str, str] = {
    "cli": CLI_COLOR,
    "mcp": MCP_COLOR,
    "gateway": GATEWAY_COLOR,
    "cli_skilled": CLI_SKILLED_COLOR,
}
MODALITY_LABELS: dict[str, str] = {
    "cli": "CLI",
    "mcp": "MCP",
    "gateway": "Gateway",
    "cli_skilled": "CLI Skilled",
}

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


def _detect_modalities(results: list[RunResult]) -> list[str]:
    """Return an ordered list of modalities present in the results."""
    seen: set[str] = {r.modality for r in results}
    # Maintain a consistent ordering
    order = ["cli", "cli_skilled", "mcp", "gateway"]
    return [m for m in order if m in seen]


def token_comparison_chart(results: list[RunResult]) -> go.Figure:
    """Grouped bar chart comparing median total tokens per modality per task.

    Includes error bars showing the p25-p75 interquartile range.
    """
    grouped = _group_by_task_and_modality(results)
    task_ids = _sorted_task_ids(grouped)
    modalities = _detect_modalities(results)

    fig = go.Figure()
    for modality in modalities:
        medians, err_minus, err_plus = [], [], []
        for tid in task_ids:
            runs = grouped[tid].get(modality, [])
            if runs:
                vals = [r.total_tokens for r in runs]
                med = float(np.median(vals))
                p25 = float(np.percentile(vals, 25))
                p75 = float(np.percentile(vals, 75))
                medians.append(med)
                err_minus.append(max(med - p25, 0))
                err_plus.append(max(p75 - med, 0))
            else:
                medians.append(0)
                err_minus.append(0)
                err_plus.append(0)
        fig.add_trace(go.Bar(
            name=MODALITY_LABELS.get(modality, modality),
            x=task_ids,
            y=medians,
            marker_color=MODALITY_COLORS.get(modality, "#888888"),
            error_y=dict(type="data", symmetric=False, array=err_plus, arrayminus=err_minus),
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
    """Box plot of wall_clock_seconds per modality, grouped by task."""
    grouped = _group_by_task_and_modality(results)
    task_ids = _sorted_task_ids(grouped)
    modalities = _detect_modalities(results)

    fig = go.Figure()
    for modality in modalities:
        x_vals: list[str] = []
        y_vals: list[float] = []
        for tid in task_ids:
            runs = grouped[tid].get(modality, [])
            for r in runs:
                x_vals.append(tid)
                y_vals.append(r.wall_clock_seconds)
        fig.add_trace(go.Box(
            name=MODALITY_LABELS.get(modality, modality),
            x=x_vals,
            y=y_vals,
            marker_color=MODALITY_COLORS.get(modality, "#888888"),
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
    """Grouped bar chart comparing median tool call counts per modality per task.

    Includes error bars showing the p25-p75 interquartile range.
    """
    grouped = _group_by_task_and_modality(results)
    task_ids = _sorted_task_ids(grouped)
    modalities = _detect_modalities(results)

    fig = go.Figure()
    for modality in modalities:
        medians, err_minus, err_plus = [], [], []
        for tid in task_ids:
            runs = grouped[tid].get(modality, [])
            if runs:
                vals = [r.tool_call_count for r in runs]
                med = float(np.median(vals))
                p25 = float(np.percentile(vals, 25))
                p75 = float(np.percentile(vals, 75))
                medians.append(med)
                err_minus.append(max(med - p25, 0))
                err_plus.append(max(p75 - med, 0))
            else:
                medians.append(0)
                err_minus.append(0)
                err_plus.append(0)
        fig.add_trace(go.Bar(
            name=MODALITY_LABELS.get(modality, modality),
            x=task_ids,
            y=medians,
            marker_color=MODALITY_COLORS.get(modality, "#888888"),
            error_y=dict(type="data", symmetric=False, array=err_plus, arrayminus=err_minus),
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
    modalities = _detect_modalities(results)

    fig = go.Figure()
    for modality in modalities:
        rates = []
        for tid in task_ids:
            runs = grouped[tid].get(modality, [])
            if runs:
                rate = sum(1 for r in runs if r.task_completed) / len(runs) * 100
                rates.append(rate)
            else:
                rates.append(0)
        fig.add_trace(go.Bar(
            name=MODALITY_LABELS.get(modality, modality),
            x=task_ids,
            y=rates,
            marker_color=MODALITY_COLORS.get(modality, "#888888"),
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
    modalities = _detect_modalities(results)

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
    for i, modality in enumerate(modalities):
        color = MODALITY_COLORS.get(modality, "#888888")
        name = MODALITY_LABELS.get(modality, modality)
        medians = []
        for tid in task_ids:
            runs = grouped[tid].get(modality, [])
            medians.append(float(np.median([r.total_tokens for r in runs])) if runs else 0)
        fig.add_trace(
            go.Bar(name=name, x=task_ids, y=medians, marker_color=color, showlegend=(i < len(modalities))),
            row=1, col=1,
        )

    # --- Latency box plot (row=1, col=2) ---
    for modality in modalities:
        color = MODALITY_COLORS.get(modality, "#888888")
        name = MODALITY_LABELS.get(modality, modality)
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
    for modality in modalities:
        color = MODALITY_COLORS.get(modality, "#888888")
        name = MODALITY_LABELS.get(modality, modality)
        medians = []
        for tid in task_ids:
            runs = grouped[tid].get(modality, [])
            medians.append(float(np.median([r.tool_call_count for r in runs])) if runs else 0)
        fig.add_trace(
            go.Bar(name=name, x=task_ids, y=medians, marker_color=color, showlegend=False),
            row=2, col=1,
        )

    # --- Completion rate (row=2, col=2) ---
    for modality in modalities:
        color = MODALITY_COLORS.get(modality, "#888888")
        name = MODALITY_LABELS.get(modality, modality)
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
