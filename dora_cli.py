#!/usr/bin/env python3
"""Standalone CLI tool that computes DORA metrics from Azure DevOps pipeline data."""

import asyncio
import base64
import calendar
import re
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx

BASE_URL = "https://dev.azure.com"
API_VERSION = "7.1"

_URL_PATTERNS = [
    re.compile(r"https?://dev\.azure\.com/([^/]+)"),
    re.compile(r"https?://([^.]+)\.visualstudio\.com"),
]


def parse_org(org: str) -> str:
    org = org.strip().rstrip("/")
    for pattern in _URL_PATTERNS:
        m = pattern.match(org)
        if m:
            return m.group(1)
    return org


def auth_header(pat: str) -> dict[str, str]:
    encoded = base64.b64encode(f":{pat}".encode()).decode()
    return {"Authorization": f"Basic {encoded}"}


def read_pat() -> str:
    pat_file = Path(__file__).parent / "env.tks"
    if not pat_file.exists():
        print("Error: env.tks not found in project root.")
        sys.exit(1)
    pat = pat_file.read_text().strip()
    if not pat:
        print("Error: env.tks is empty.")
        sys.exit(1)
    return pat


def parse_dt(s: str | None) -> datetime | None:
    if not s:
        return None
    # Azure DevOps returns ISO 8601 with trailing Z or offset
    s = s.replace("Z", "+00:00")
    return datetime.fromisoformat(s)


def prompt_choice(items: list[str], label: str, allow_all: bool = False) -> int | None:
    """Display numbered list, return selected index or None for 'all'."""
    for i, item in enumerate(items, 1):
        print(f"  {i}. {item}")
    if allow_all:
        print(f"  0. (All)")
    while True:
        raw = input(f"\nSelect {label}: ").strip()
        if not raw.isdigit():
            print("Please enter a number.")
            continue
        n = int(raw)
        if allow_all and n == 0:
            return None
        if 1 <= n <= len(items):
            return n - 1
        print(f"Please enter a number between {'0' if allow_all else '1'} and {len(items)}.")


async def api_get(client: httpx.AsyncClient, url: str, pat: str, params: dict | None = None) -> dict:
    all_params = {"api-version": API_VERSION}
    if params:
        all_params.update(params)
    resp = await client.get(url, headers=auth_header(pat), params=all_params, timeout=30)
    resp.raise_for_status()
    return resp.json()


async def fetch_projects(client: httpx.AsyncClient, org: str, pat: str) -> list[dict]:
    data = await api_get(client, f"{BASE_URL}/{org}/_apis/projects", pat)
    return sorted(data["value"], key=lambda p: p["name"].lower())


async def fetch_pipelines(client: httpx.AsyncClient, org: str, project: str, pat: str) -> list[dict]:
    data = await api_get(client, f"{BASE_URL}/{org}/{project}/_apis/pipelines", pat)
    return sorted(data["value"], key=lambda p: p["name"].lower())


async def fetch_builds(client: httpx.AsyncClient, org: str, project: str, definition_id: int, pat: str) -> list[dict]:
    six_months_ago = datetime.now(UTC) - timedelta(days=180)
    data = await api_get(
        client,
        f"{BASE_URL}/{org}/{project}/_apis/build/builds",
        pat,
        params={
            "definitions": str(definition_id),
            "minTime": six_months_ago.isoformat(),
            "queryOrder": "finishTimeDescending",
            "$top": 500,
        },
    )
    return data["value"]


async def fetch_commit(client: httpx.AsyncClient, org: str, project: str, repo_id: str, commit_id: str, pat: str) -> dict | None:
    url = f"{BASE_URL}/{org}/{project}/_apis/git/repositories/{repo_id}/commits/{commit_id}"
    try:
        data = await api_get(client, url, pat)
        return data
    except httpx.HTTPStatusError:
        return None


# ---------------------------------------------------------------------------
# Helpers: group builds by month
# ---------------------------------------------------------------------------

def month_key(b: dict) -> str | None:
    ft = b.get("finishTime")
    if not ft:
        return None
    return parse_dt(ft).strftime("%Y-%m")


def builds_by_month(builds: list[dict]) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = {}
    for b in builds:
        mk = month_key(b)
        if mk:
            groups.setdefault(mk, []).append(b)
    return dict(sorted(groups.items()))


def all_months_in_range(builds: list[dict]) -> list[str]:
    """Return sorted list of YYYY-MM keys covering the full 6-month window."""
    now = datetime.now(UTC)
    months = []
    for i in range(6, 0, -1):
        dt = now - timedelta(days=30 * i)
        months.append(dt.strftime("%Y-%m"))
    current = now.strftime("%Y-%m")
    if current not in months:
        months.append(current)
    return sorted(set(months))


# ---------------------------------------------------------------------------
# DORA metric computation
# ---------------------------------------------------------------------------

def compute_deployment_frequency(builds: list[dict]) -> dict:
    """Successful deployments per day, broken down by month."""
    successful = [b for b in builds if b.get("result") == "succeeded" and b.get("finishTime")]
    months: dict[str, list[datetime]] = {}
    for b in successful:
        dt = parse_dt(b["finishTime"])
        key = dt.strftime("%Y-%m")
        months.setdefault(key, []).append(dt)

    monthly = {}
    for key in sorted(months):
        year, month = map(int, key.split("-"))
        days_in_month = calendar.monthrange(year, month)[1]
        count = len(months[key])
        days_per_dep = days_in_month / count if count else None
        monthly[key] = {"count": count, "days_per_dep": days_per_dep}

    total_days = 180
    total_deploys = len(successful)
    overall = total_days / total_deploys if total_deploys else None
    return {"monthly": monthly, "overall_days_per_dep": overall, "total": total_deploys}


async def compute_lead_times_by_month(
    client: httpx.AsyncClient, org: str, builds: list[dict], pat: str
) -> dict[str, dict]:
    """Lead time per month. Returns {month: {avg_hours, sample_size}}."""
    successful = [
        b for b in builds
        if b.get("result") == "succeeded" and b.get("finishTime") and b.get("sourceVersion")
    ]
    # Fetch commit data for up to 200 builds
    sample = successful[:200]
    # Build a list of (month_key, lead_time_seconds)
    lead_times_by_month: dict[str, list[float]] = {}

    for b in sample:
        repo = b.get("repository", {})
        repo_id = repo.get("id")
        commit_id = b.get("sourceVersion")
        build_project = b.get("project", {}).get("name", "")
        if not repo_id or not commit_id or not build_project:
            continue
        commit = await fetch_commit(client, org, build_project, repo_id, commit_id, pat)
        if not commit:
            continue
        author_date = parse_dt(commit.get("author", {}).get("date"))
        finish_time = parse_dt(b["finishTime"])
        if author_date and finish_time:
            delta = (finish_time - author_date).total_seconds()
            if delta >= 0:
                mk = finish_time.strftime("%Y-%m")
                lead_times_by_month.setdefault(mk, []).append(delta)

    result: dict[str, dict] = {}
    all_times: list[float] = []
    for mk in sorted(lead_times_by_month):
        times = lead_times_by_month[mk]
        avg = sum(times) / len(times)
        result[mk] = {"avg_hours": avg / 3600, "sample_size": len(times)}
        all_times.extend(times)

    result["_overall"] = {"avg_hours": None, "sample_size": 0}
    if all_times:
        result["_overall"] = {"avg_hours": sum(all_times) / len(all_times) / 3600, "sample_size": len(all_times)}
    return result


def compute_change_failure_rate_by_month(builds: list[dict]) -> dict[str, dict]:
    """CFR per month. Returns {month: {rate_pct, failed, total}}."""
    grouped = builds_by_month(builds)
    result: dict[str, dict] = {}
    all_failed = 0
    all_completed = 0
    for mk, month_builds in grouped.items():
        completed = [b for b in month_builds if b.get("result") in ("succeeded", "failed", "partiallySucceeded")]
        failed = [b for b in completed if b.get("result") in ("failed", "partiallySucceeded")]
        all_failed += len(failed)
        all_completed += len(completed)
        result[mk] = {"rate_pct": None, "failed": 0, "total": 0}
        if completed:
            result[mk] = {"rate_pct": len(failed) / len(completed) * 100, "failed": len(failed), "total": len(completed)}
    result["_overall"] = {"rate_pct": None, "failed": 0, "total": 0}
    if all_completed:
        result["_overall"] = {"rate_pct": all_failed / all_completed * 100, "failed": all_failed, "total": all_completed}
    return result


def compute_mttr_by_month(builds: list[dict]) -> dict[str, dict]:
    """MTTR per month. Recovery incidents are assigned to the month of the recovery build."""
    by_pipeline: dict[int, list[dict]] = {}
    for b in builds:
        if not b.get("finishTime") or b.get("result") not in ("succeeded", "failed", "partiallySucceeded"):
            continue
        def_id = b.get("definition", {}).get("id")
        if def_id is None:
            continue
        by_pipeline.setdefault(def_id, []).append(b)

    # Collect (month_key, recovery_seconds) pairs
    recovery_by_month: dict[str, list[float]] = {}
    for def_id, pipeline_builds in by_pipeline.items():
        sorted_builds = sorted(pipeline_builds, key=lambda b: parse_dt(b["finishTime"]))
        last_failure_time = None
        for b in sorted_builds:
            is_failure = b["result"] in ("failed", "partiallySucceeded")
            is_recovery = b["result"] == "succeeded" and last_failure_time is not None
            if is_failure and last_failure_time is None:
                last_failure_time = parse_dt(b["finishTime"])
                continue
            if is_recovery:
                recovery_time = parse_dt(b["finishTime"])
                recovery = (recovery_time - last_failure_time).total_seconds()
                if recovery >= 0:
                    mk = recovery_time.strftime("%Y-%m")
                    recovery_by_month.setdefault(mk, []).append(recovery)
                last_failure_time = None

    result: dict[str, dict] = {}
    all_recoveries: list[float] = []
    for mk in sorted(recovery_by_month):
        times = recovery_by_month[mk]
        avg = sum(times) / len(times)
        result[mk] = {"avg_hours": avg / 3600, "incidents": len(times)}
        all_recoveries.extend(times)

    result["_overall"] = {"avg_hours": None, "incidents": 0}
    if all_recoveries:
        result["_overall"] = {"avg_hours": sum(all_recoveries) / len(all_recoveries) / 3600, "incidents": len(all_recoveries)}
    return result


def classify_dora(metric: str, value: float | None) -> str:
    """Return DORA performance category."""
    if value is None:
        return "N/A"
    if metric == "deploy_freq":
        # days per deployment (lower is better)
        if value <= 1:
            return "Elite"
        if value <= 7:
            return "High"
        if value <= 30:
            return "Medium"
        return "Low"
    if metric == "lead_time":
        # hours
        if value < 24:
            return "Elite"
        if value < 24 * 7:
            return "High"
        if value < 24 * 30:
            return "Medium"
        return "Low"
    if metric == "cfr":
        # percentage
        if value <= 5:
            return "Elite"
        if value <= 10:
            return "High"
        if value <= 15:
            return "Medium"
        return "Low"
    if metric == "mttr":
        # hours
        if value < 1:
            return "Elite"
        if value < 24:
            return "High"
        if value < 24 * 7:
            return "Medium"
        return "Low"
    return "N/A"


def format_hours(h: float | None) -> str:
    if h is None:
        return "N/A"
    if h < 1:
        return f"{h * 60:.0f} minutes"
    if h < 48:
        return f"{h:.1f} hours"
    return f"{h / 24:.1f} days"


def print_results(df: dict, lt: dict, cfr: dict, mttr: dict, months: list[str], title: str = ""):
    col_w = 14
    label_w = 28
    cols = months + ["OVERALL"]
    w = label_w + col_w * len(cols) + 2
    sep = "─" * w

    header = title if title else "DORA METRICS REPORT"
    report_date = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

    print("\n" + "=" * w)
    print(f"  {header}")
    print(f"  Generated: {report_date}")
    print("=" * w)

    # Header row
    hdr = f"  {'Metric':<{label_w}}"
    for c in cols:
        hdr += f"{c:>{col_w}}"
    print(f"\n{sep}")
    print(hdr)
    print(sep)

    # Helper to get overall values
    lt_overall = lt.get("_overall", {})
    cfr_overall = cfr.get("_overall", {})
    mttr_overall = mttr.get("_overall", {})

    # Row 1: Deployment Frequency (days/deploy)
    row = f"  {'Deploy Freq (days/dep)':<{label_w}}"
    for mk in months:
        df_m = df["monthly"].get(mk)
        dpd = df_m["days_per_dep"] if df_m else None
        val = f"{dpd:.1f}" if dpd is not None else "N/A"
        row += f"{val:>{col_w}}"
    ov = f"{df['overall_days_per_dep']:.1f}" if df["overall_days_per_dep"] is not None else "N/A"
    row += f"{ov}".rjust(col_w)
    print(row)

    # Row 2: Deploy count
    row = f"  {'  (total deploys)':<{label_w}}"
    for mk in months:
        df_m = df["monthly"].get(mk)
        val = str(df_m["count"]) if df_m else "0"
        row += f"{val:>{col_w}}"
    row += f"{df['total']}".rjust(col_w)
    print(row)

    print(sep)

    # Row 3: Lead Time for Changes
    row = f"  {'Lead Time for Changes':<{label_w}}"
    for mk in months:
        lt_m = lt.get(mk)
        val = format_hours(lt_m["avg_hours"]) if lt_m else "N/A"
        row += f"{val:>{col_w}}"
    row += f"{format_hours(lt_overall.get('avg_hours'))}".rjust(col_w)
    print(row)

    # Row 4: Lead time sample size
    row = f"  {'  (sample size)':<{label_w}}"
    for mk in months:
        lt_m = lt.get(mk)
        val = str(lt_m["sample_size"]) if lt_m else "0"
        row += f"{val:>{col_w}}"
    row += f"{lt_overall.get('sample_size', 0)}".rjust(col_w)
    print(row)

    print(sep)

    # Row 5: Change Failure Rate
    row = f"  {'Change Failure Rate':<{label_w}}"
    for mk in months:
        cfr_m = cfr.get(mk)
        rate = cfr_m["rate_pct"] if cfr_m else None
        val = f"{rate:.1f}%" if rate is not None else "N/A"
        row += f"{val:>{col_w}}"
    cfr_ov = f"{cfr_overall['rate_pct']:.1f}%" if cfr_overall.get("rate_pct") is not None else "N/A"
    row += f"{cfr_ov}".rjust(col_w)
    print(row)

    # Row 6: CFR detail
    row = f"  {'  (failed / total)':<{label_w}}"
    for mk in months:
        cfr_m = cfr.get(mk, {"failed": 0, "total": 0})
        val = f"{cfr_m['failed']}/{cfr_m['total']}"
        row += f"{val:>{col_w}}"
    row += f"{cfr_overall.get('failed', 0)}/{cfr_overall.get('total', 0)}".rjust(col_w)
    print(row)

    print(sep)

    # Row 7: MTTR
    row = f"  {'MTTR':<{label_w}}"
    for mk in months:
        mttr_m = mttr.get(mk)
        val = format_hours(mttr_m["avg_hours"]) if mttr_m else "N/A"
        row += f"{val:>{col_w}}"
    row += f"{format_hours(mttr_overall.get('avg_hours'))}".rjust(col_w)
    print(row)

    # Row 8: MTTR incidents
    row = f"  {'  (incidents)':<{label_w}}"
    for mk in months:
        mttr_m = mttr.get(mk)
        val = str(mttr_m["incidents"]) if mttr_m else "0"
        row += f"{val:>{col_w}}"
    row += f"{mttr_overall.get('incidents', 0)}".rjust(col_w)
    print(row)

    print(sep)

    # DORA categories row
    print(f"\n{sep}")
    print("  DORA PERFORMANCE CATEGORIES")
    print(sep)

    for metric_key, metric_label, get_val in [
        ("deploy_freq", "Deploy Frequency", lambda mk: (df["monthly"].get(mk, {}) or {}).get("days_per_dep")),
        ("lead_time", "Lead Time", lambda mk: (lt.get(mk) or {}).get("avg_hours")),
        ("cfr", "Change Failure Rate", lambda mk: (cfr.get(mk) or {}).get("rate_pct")),
        ("mttr", "MTTR", lambda mk: (mttr.get(mk) or {}).get("avg_hours")),
    ]:
        row = f"  {metric_label:<{label_w}}"
        for mk in months:
            val = get_val(mk)
            cat = classify_dora(metric_key, val)
            row += f"{cat:>{col_w}}"
        # Overall
        overall_values = {
            "deploy_freq": df["overall_days_per_dep"],
            "lead_time": lt_overall.get("avg_hours"),
            "cfr": cfr_overall.get("rate_pct"),
            "mttr": mttr_overall.get("avg_hours"),
        }
        row += f"{classify_dora(metric_key, overall_values[metric_key])}".rjust(col_w)
        print(row)

    print(f"\n{'=' * w}")
    print("  Legend: Elite > High > Medium > Low")
    print("=" * w)


async def main():
    print("=" * 50)
    print("  DORA Metrics CLI — Azure DevOps")
    print("=" * 50)

    pat = read_pat()
    print("\nPAT loaded from env.tks")

    org_input = input("\nEnter Azure DevOps organization (name or URL): ").strip()
    if not org_input:
        print("No organization provided.")
        sys.exit(1)
    org = parse_org(org_input)
    print(f"Organization: {org}")

    async with httpx.AsyncClient() as client:
        # Fetch projects
        print("\nFetching projects...")
        try:
            projects = await fetch_projects(client, org, pat)
        except httpx.HTTPStatusError as e:
            print(f"Error fetching projects: {e.response.status_code} {e.response.text[:200]}")
            sys.exit(1)

        if not projects:
            print("No projects found.")
            sys.exit(1)

        print(f"\nFound {len(projects)} project(s):")
        proj_choice = prompt_choice([p["name"] for p in projects], "a project (0 for all)", allow_all=True)
        selected_projects = projects if proj_choice is None else [projects[proj_choice]]
        print(f"\nSelected project(s): {', '.join(p['name'] for p in selected_projects)}")

        run_per_project = len(selected_projects) > 1

        # Collect builds per project
        project_builds: dict[str, list[dict]] = {}
        for proj in selected_projects:
            pname = proj["name"]
            print(f"\nFetching pipelines for '{pname}'...")
            pipelines = await fetch_pipelines(client, org, pname, pat)
            if not pipelines:
                print(f"  No pipelines found in '{pname}', skipping.")
                continue

            # Only prompt for pipeline selection when a single project is selected
            if not run_per_project:
                print(f"\nFound {len(pipelines)} pipeline(s):")
                choice = prompt_choice([p["name"] for p in pipelines], "a pipeline (0 for all)", allow_all=True)
                selected_pipelines = pipelines if choice is None else [pipelines[choice]]
                print(f"\nSelected: {', '.join(p['name'] for p in selected_pipelines)}")
            if run_per_project:
                selected_pipelines = pipelines
                print(f"  Found {len(pipelines)} pipeline(s), fetching all...")

            proj_builds: list[dict] = []
            for p in selected_pipelines:
                print(f"  Fetching builds for '{pname}/{p['name']}'...")
                builds = await fetch_builds(client, org, pname, p["id"], pat)
                print(f"    → {len(builds)} builds")
                proj_builds.extend(builds)
            if proj_builds:
                project_builds[pname] = proj_builds

        if not project_builds:
            print("\nNo builds found in the past 6 months.")
            sys.exit(1)

        # When running per project, compute and print metrics for each project separately
        if run_per_project:
            for pname, builds in project_builds.items():
                print(f"\n{'#' * 40}")
                print(f"  Computing metrics for '{pname}' ({len(builds)} builds)...")
                months = all_months_in_range(builds)
                df = compute_deployment_frequency(builds)
                cfr = compute_change_failure_rate_by_month(builds)
                mttr_result = compute_mttr_by_month(builds)
                print(f"  Fetching commit data for lead time...")
                lt = await compute_lead_times_by_month(client, org, builds, pat)
                print_results(df, lt, cfr, mttr_result, months, title=f"DORA METRICS — {pname}")

        # Single project mode
        if not run_per_project:
            all_builds = list(project_builds.values())[0]
            pname = list(project_builds.keys())[0]
            print(f"\nTotal builds: {len(all_builds)}")
            print("\nComputing metrics...")
            months = all_months_in_range(all_builds)
            df = compute_deployment_frequency(all_builds)
            cfr = compute_change_failure_rate_by_month(all_builds)
            mttr_result = compute_mttr_by_month(all_builds)
            print("Fetching commit data for lead time (this may take a moment)...")
            lt = await compute_lead_times_by_month(client, org, all_builds, pat)
            print_results(df, lt, cfr, mttr_result, months, title=f"DORA METRICS — {pname}")


if __name__ == "__main__":
    asyncio.run(main())
