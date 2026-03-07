#!/usr/bin/env python3
"""
End-to-end test runner for DORA Explorer.

Loads pre-generated mock build data from tests/mock_data/, constructs mock
Azure DevOps HTTP responses, runs the full metric computation pipeline, and
exports JSON + Excel + PNG chart reports to reports/.

Usage:
    python tests/run_tests.py
"""

import asyncio
import json
import sys
from datetime import datetime, UTC
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

# Make project root importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dora_metrics import (
    compute_change_failure_rate_by_month,
    compute_deployment_frequency,
    compute_lead_times_by_month,
    compute_mttr_by_month,
)
from dora_charts import generate_charts as export_charts
from dora_cli import export_excel, export_json
from chart_from_excel import generate_from_excel

MOCK_DATA_DIR = Path(__file__).parent / "mock_data"
TEAMS = ["alpha", "bravo", "charlie", "delta"]


# ── Mock HTTP client ───────────────────────────────────────────────────────────

def build_mock_client(commit_lookup: dict[str, str]):
    """
    Return an AsyncMock httpx.AsyncClient whose .get() serves Azure DevOps
    commit responses from the pre-generated commit_lookup dict.
    """
    def iso_fallback():
        return datetime(2025, 9, 1, tzinfo=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    async def mock_get(url: str, **kwargs):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()

        parts = [p for p in url.split("/") if p]
        if "commits" in parts:
            sha = parts[-1].split("?")[0]
            commit_date = commit_lookup.get(sha, iso_fallback())
            resp.json = MagicMock(return_value={
                "commitId": sha,
                "author": {
                    "name":  "Dev",
                    "email": "dev@elia-digitization.mock",
                    "date":  commit_date,
                },
                "comment": "mock commit",
            })
        else:
            resp.json = MagicMock(return_value={"value": []})

        return resp

    client = AsyncMock()
    client.get = mock_get
    return client


# ── Per-team pipeline ──────────────────────────────────────────────────────────

async def run_team(data: dict) -> None:
    meta    = data["metadata"]
    builds  = data["builds"]
    commits = data["commits"]

    team   = meta["team"]
    org    = meta["org"]
    mode   = meta["mode"]
    months = meta["months"]

    print(f"\n{'─' * 60}")
    print(f"  {team}")
    print(f"  Weakness : {meta['weakness']}")
    print(f"  Improve  : {meta['improve']}")
    print(f"  Builds   : {meta['stats']['total_builds']} "
          f"({meta['stats']['succeeded']} ok / {meta['stats']['failed']} fail, "
          f"CFR≈{meta['stats']['cfr_approx_pct']}%, "
          f"DF≈{meta['stats']['df_approx_days']} d/dep)")
    print()

    client = build_mock_client(commits)

    # ── Run all four compute functions (real code, mocked HTTP) ──
    df_r   = compute_deployment_frequency(builds)
    lt_r   = await compute_lead_times_by_month(client, org, builds, "mock-pat")
    cfr_r  = compute_change_failure_rate_by_month(builds)
    mttr_r = compute_mttr_by_month(builds)

    # ── Export all three report formats ──────────────────────────
    export_json(  org, team, mode, months, df_r, lt_r, cfr_r, mttr_r)
    export_excel( org, team, mode, months, df_r, lt_r, cfr_r, mttr_r)
    export_charts(team, mode, months, df_r, lt_r, cfr_r, mttr_r)


# ── Main ───────────────────────────────────────────────────────────────────────

async def main():
    print("=" * 60)
    print("  DORA Explorer — End-to-End Test Suite")
    print("  Mock data: tests/mock_data/  →  Reports: reports/")
    print("=" * 60)

    for team_key in TEAMS:
        path = MOCK_DATA_DIR / f"{team_key}_team.json"
        if not path.exists():
            print(f"\n  [SKIP] {path.name} not found — run generate_mock_data.py first")
            continue
        data = json.loads(path.read_text())
        await run_team(data)

    # ── Excel-based teams ─────────────────────────────────────────
    excel_fixtures = [
        Path(__file__).resolve().parent.parent / "DORA_DB_Zulu.xlsx",
    ]
    for xl in excel_fixtures:
        if not xl.exists():
            print(f"\n  [SKIP] {xl.name} not found")
            continue
        print(f"\n{'─' * 60}")
        print(f"  Excel fixture: {xl.name}")
        generate_from_excel(xl)

    print(f"\n{'=' * 60}")
    print("  All reports written to reports/")
    print("=" * 60)

    # List generated files
    reports_dir = Path(__file__).resolve().parent.parent / "reports"
    files = sorted(reports_dir.iterdir(), key=lambda f: f.name)
    for f in files:
        if not f.name.startswith("."):
            print(f"  {f.name}")


if __name__ == "__main__":
    asyncio.run(main())
