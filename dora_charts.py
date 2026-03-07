"""DORA Metrics chart generation — standalone module.

Call ``generate_charts()`` with pre-computed metric dicts (or data read
directly from an Excel workbook) to produce a branded PNG report.
"""

from datetime import datetime
from pathlib import Path

from dora_metrics import classify_dora


# ── Elia brand palette ────────────────────────────────────────────────────────
ELIA_ORANGE = "#FF7300"
ELIA_DARK   = "#EEEEEE"
ELIA_PETROL = "#004B5A"
ELIA_LIGHT  = "#111111"
ELIA_MID    = "#333333"
BG          = "#000000"

C_ELITE = "#00C853"
C_HIGH  = "#64DD17"
C_MED   = "#FFD600"
C_LOW   = "#FF3D00"
LEVEL_COLOR = {"Elite": C_ELITE, "High": C_HIGH, "Medium": C_MED, "Low": C_LOW}


def _bar_color(level: str) -> str:
    return LEVEL_COLOR.get(level, "#AAAAAA")


def _fmt_month(mk: str) -> str:
    return datetime.strptime(mk, "%Y-%m").strftime("%b'%y")


def generate_charts(
    project: str,
    mode: str,
    months: list[str],
    df: dict,
    lt: dict,
    cfr: dict,
    mttr: dict,
    output_dir: Path | None = None,
) -> str:
    """Generate a 4-panel DORA metrics PNG chart.

    Parameters
    ----------
    project:    Display name shown in the chart header.
    mode:       Mode label (e.g. "pipelines" or "pullrequests").
    months:     Ordered list of "YYYY-MM" strings defining the x-axis.
    df:         Deployment-frequency result dict from ``compute_deployment_frequency``.
    lt:         Lead-time result dict from ``compute_lead_times_by_month``.
    cfr:        Change-failure-rate result dict from ``compute_change_failure_rate_by_month``.
    mttr:       MTTR result dict from ``compute_mttr_by_month``.
    output_dir: Directory to write the PNG to.  Defaults to ``<repo-root>/reports/``.

    Returns
    -------
    Absolute path of the generated PNG file.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.gridspec as gridspec

    xlabels = [_fmt_month(m) for m in months]

    # ── Extract monthly series ─────────────────────────────────────────────────
    df_vals   = [df.get("monthly", {}).get(m, {}).get("days_per_dep")  for m in months]
    lt_vals   = [lt.get(m, {}).get("avg_hours")                         for m in months]
    cfr_vals  = [cfr.get(m, {}).get("rate_pct")                         for m in months]
    mttr_vals = [mttr.get(m, {}).get("avg_hours")                       for m in months]

    df_ov   = df.get("overall_days_per_dep")
    lt_ov   = lt.get("_overall", {}).get("avg_hours")
    cfr_ov  = cfr.get("_overall", {}).get("rate_pct")
    mttr_ov = mttr.get("_overall", {}).get("avg_hours")

    # ── Figure ────────────────────────────────────────────────────────────────
    fig = plt.figure(figsize=(16, 10), facecolor=BG)

    gs = gridspec.GridSpec(
        3, 2, figure=fig,
        top=0.84, bottom=0.07,
        left=0.06, right=0.97,
        hspace=0.55, wspace=0.25,
        height_ratios=[1, 1, 0.08],
    )

    # ── Header band ───────────────────────────────────────────────────────────
    ax_hdr = fig.add_axes([0, 0.94, 1.0, 0.06])
    ax_hdr.set_xlim(0, 1); ax_hdr.set_ylim(0, 1); ax_hdr.axis("off")
    ax_hdr.add_patch(plt.Rectangle((0, 0), 1, 1, fc=ELIA_ORANGE, ec="none",
                                    transform=ax_hdr.transAxes, zorder=0))
    ax_hdr.text(0.02, 0.50, project, fontsize=18, fontweight="bold",
                color=BG, va="center", transform=ax_hdr.transAxes)
    ax_hdr.text(0.98, 0.50,
                f"Mode: {mode}   |   Period: {xlabels[0]} – {xlabels[-1]}",
                fontsize=10, color=BG, alpha=0.88, va="center", ha="right",
                transform=ax_hdr.transAxes)

    # ── Per-metric chart helper ───────────────────────────────────────────────
    def draw_metric(ax, title, values, overall_val, metric_key, fmt_bar, fmt_kpi, thresholds):
        ax.set_facecolor(ELIA_LIGHT)
        for sp in ax.spines.values():
            sp.set_edgecolor(ELIA_MID)
        ax.yaxis.grid(True, color=ELIA_MID, linewidth=0.8, zorder=0)
        ax.set_axisbelow(True)

        n = len(values)
        max_v = max((v for v in values if v is not None), default=1) or 1

        bar_meta = []
        for i, v in enumerate(values):
            if v is None:
                ax.bar(i, 0.001, color="#444444", alpha=0.4, width=0.62, zorder=2)
                ax.text(i, max_v * 0.04, "N/A", ha="center", va="bottom",
                        fontsize=7, color="#666666", zorder=3)
            else:
                level = classify_dora(metric_key, v)
                color = _bar_color(level)
                ax.bar(i, v, color=color, width=0.62, zorder=2, alpha=0.90,
                       edgecolor="white", linewidth=0.4)
                bar_meta.append((i, v, level, color))

        for i, v, _, color in bar_meta:
            ax.text(i, v + max_v * 0.025, fmt_bar(v),
                    ha="center", va="bottom", fontsize=7.5,
                    fontweight="bold", color=ELIA_DARK, zorder=3)

        if thresholds:
            for tv, tc, tlbl in thresholds:
                if tv <= max_v * 1.3:
                    ax.axhline(tv, color=tc, linewidth=1.2, linestyle="--",
                               alpha=0.75, zorder=1)
                    ax.text(n - 0.5, tv * 1.02, tlbl,
                            fontsize=6, color=tc, va="bottom", ha="right")

        ax.set_xticks(range(n))
        ax.set_xticklabels(xlabels, fontsize=8.5, color=ELIA_DARK, rotation=0)
        ax.tick_params(axis="y", labelsize=8, labelcolor="#AAAAAA")
        ax.set_xlim(-0.6, n - 0.4)
        ax.set_ylim(0, max_v * 1.38)

        ax.text(-0.01, 1.08, title, transform=ax.transAxes,
                fontsize=10.5, fontweight="bold", color=ELIA_DARK, va="top")

        if overall_val is not None:
            level = classify_dora(metric_key, overall_val)
            lc = _bar_color(level)
            ax.text(1.01, 1.08, fmt_kpi(overall_val), transform=ax.transAxes,
                    fontsize=20, fontweight="bold", color=lc, va="top", ha="right")
            ax.text(1.01, 0.97, f"▶ {level}", transform=ax.transAxes,
                    fontsize=8.5, fontweight="bold", color=lc, va="top", ha="right")
        else:
            ax.text(1.01, 1.08, "N/A", transform=ax.transAxes,
                    fontsize=20, fontweight="bold", color="#555555",
                    va="top", ha="right")

        ax.axvline(-0.6, color=ELIA_PETROL, linewidth=3, zorder=4, clip_on=False)

    # ── Four metric charts ────────────────────────────────────────────────────
    draw_metric(
        fig.add_subplot(gs[0, 0]),
        "Deployment Frequency (days / deploy)",
        df_vals, df_ov, "deploy_freq",
        fmt_bar=lambda v: f"{v:.1f}d",
        fmt_kpi=lambda v: f"{v:.1f}d",
        thresholds=[(1, C_ELITE, "Elite ≤1d"), (7, C_HIGH, "High ≤7d"), (30, C_MED, "Med ≤30d")],
    )
    draw_metric(
        fig.add_subplot(gs[0, 1]),
        "Lead Time for Changes (hrs)",
        lt_vals, lt_ov, "lead_time",
        fmt_bar=lambda v: f"{v:.0f}h" if v < 100 else f"{v/24:.1f}d",
        fmt_kpi=lambda v: f"{v:.0f}h" if v < 100 else f"{v/24:.1f}d",
        thresholds=[(24, C_ELITE, "Elite <24h"), (168, C_HIGH, "High <7d"), (720, C_MED, "Med <30d")],
    )
    draw_metric(
        fig.add_subplot(gs[1, 0]),
        "Change Failure Rate (%)",
        cfr_vals, cfr_ov, "cfr",
        fmt_bar=lambda v: f"{v:.1f}%",
        fmt_kpi=lambda v: f"{v:.1f}%",
        thresholds=[(5, C_ELITE, "Elite ≤5%"), (10, C_HIGH, "High ≤10%"), (15, C_MED, "Med ≤15%")],
    )
    draw_metric(
        fig.add_subplot(gs[1, 1]),
        "Mean Time to Recovery (hrs)",
        mttr_vals, mttr_ov, "mttr",
        fmt_bar=lambda v: f"{v:.1f}h",
        fmt_kpi=lambda v: f"{v:.1f}h",
        thresholds=[(1, C_ELITE, "Elite <1h"), (24, C_HIGH, "High <24h"), (168, C_MED, "Med <7d")],
    )

    # ── Legend strip ──────────────────────────────────────────────────────────
    ax_leg = fig.add_subplot(gs[2, :])
    ax_leg.axis("off")
    for idx, (lbl, lc) in enumerate([
        ("■  Elite",     C_ELITE),
        ("■  High",      C_HIGH),
        ("■  Medium",    C_MED),
        ("■  Low",       C_LOW),
        ("--  Threshold", "#888888"),
    ]):
        ax_leg.text(0.04 + idx * 0.14, 0.5, lbl, fontsize=8.5,
                    color=lc, va="center", ha="left",
                    transform=ax_leg.transAxes, fontweight="bold")

    # ── Footer ────────────────────────────────────────────────────────────────
    fig.text(0.5, 0.01,
             f"DORA Explorer  |  Generated {datetime.now().strftime('%d %b %Y')}",
             ha="center", fontsize=8, color="#666666")

    # ── Save ──────────────────────────────────────────────────────────────────
    if output_dir is None:
        output_dir = Path(__file__).resolve().parent / "reports"
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_project = project.replace(" ", "_")
    filepath = output_dir / f"DORA_chart_{safe_project}_{mode}_{timestamp}.png"
    fig.savefig(filepath, dpi=150, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    print(f"Chart exported to: {filepath}")
    return str(filepath)
