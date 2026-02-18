"""DORA metric computation — pipeline and PR modes."""

import calendar
from datetime import UTC, datetime, timedelta

import httpx

from azure_api import fetch_commit, fetch_pr_commits, parse_dt


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


def all_months_in_range(items: list[dict]) -> list[str]:
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
# Pipeline-mode DORA metric computation
# ---------------------------------------------------------------------------

def compute_deployment_frequency(builds: list[dict]) -> dict:
    """Successful deployments per day, broken down by month."""
    successful = [b for b in builds if b.get("result") == "succeeded" and b.get("finishTime")]
    months: dict[str, list[datetime]] = {}
    details: dict[str, list[dict]] = {}
    for b in successful:
        dt = parse_dt(b["finishTime"])
        key = dt.strftime("%Y-%m")
        months.setdefault(key, []).append(dt)
        details.setdefault(key, []).append({
            "date": b["finishTime"],
            "pipeline": b.get("definition", {}).get("name", ""),
            "build_id": b.get("id"),
        })

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
    return {"monthly": monthly, "overall_days_per_dep": overall, "total": total_deploys, "_details": details}


async def compute_lead_times_by_month(
    client: httpx.AsyncClient, org: str, builds: list[dict], pat: str
) -> dict[str, dict]:
    """Lead time per month. Returns {month: {avg_hours, sample_size}}."""
    successful = [
        b for b in builds
        if b.get("result") == "succeeded" and b.get("finishTime") and b.get("sourceVersion")
    ]
    sample = successful[:200]
    lead_times_by_month: dict[str, list[float]] = {}
    details: dict[str, list[dict]] = {}

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
                details.setdefault(mk, []).append({
                    "commit_date": commit.get("author", {}).get("date", ""),
                    "finish_date": b["finishTime"],
                    "lead_time_hours": round(delta / 3600, 2),
                    "pipeline": b.get("definition", {}).get("name", ""),
                    "build_id": b.get("id"),
                })

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
    result["_details"] = details
    return result


def compute_change_failure_rate_by_month(builds: list[dict]) -> dict[str, dict]:
    """CFR per month. Returns {month: {rate_pct, failed, total}}."""
    grouped = builds_by_month(builds)
    result: dict[str, dict] = {}
    details: dict[str, list[dict]] = {}
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
        for b in completed:
            details.setdefault(mk, []).append({
                "date": b.get("finishTime", ""),
                "pipeline": b.get("definition", {}).get("name", ""),
                "result": b.get("result", ""),
                "build_id": b.get("id"),
            })
    result["_overall"] = {"rate_pct": None, "failed": 0, "total": 0}
    if all_completed:
        result["_overall"] = {"rate_pct": all_failed / all_completed * 100, "failed": all_failed, "total": all_completed}
    result["_details"] = details
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

    recovery_by_month: dict[str, list[float]] = {}
    details: dict[str, list[dict]] = {}
    for def_id, pipeline_builds in by_pipeline.items():
        sorted_builds = sorted(pipeline_builds, key=lambda b: parse_dt(b["finishTime"]))
        last_failure_time = None
        last_failure_build = None
        for b in sorted_builds:
            is_failure = b["result"] in ("failed", "partiallySucceeded")
            is_recovery = b["result"] == "succeeded" and last_failure_time is not None
            if is_failure and last_failure_time is None:
                last_failure_time = parse_dt(b["finishTime"])
                last_failure_build = b
                continue
            if is_recovery:
                recovery_time = parse_dt(b["finishTime"])
                recovery = (recovery_time - last_failure_time).total_seconds()
                if recovery >= 0:
                    mk = recovery_time.strftime("%Y-%m")
                    recovery_by_month.setdefault(mk, []).append(recovery)
                    details.setdefault(mk, []).append({
                        "failure_date": last_failure_build.get("finishTime", ""),
                        "recovery_date": b.get("finishTime", ""),
                        "duration_hours": round(recovery / 3600, 2),
                        "pipeline": b.get("definition", {}).get("name", ""),
                    })
                last_failure_time = None
                last_failure_build = None

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
    result["_details"] = details
    return result


# ---------------------------------------------------------------------------
# PR-mode DORA metric computation
# ---------------------------------------------------------------------------

def compute_pr_deployment_frequency(prs: list[dict]) -> dict:
    """Merged PRs per month, measured as days between approvals."""
    merged = [pr for pr in prs if pr.get("status") == "completed" and pr.get("closedDate")]
    months: dict[str, list[datetime]] = {}
    details: dict[str, list[dict]] = {}
    for pr in merged:
        dt = parse_dt(pr["closedDate"])
        key = dt.strftime("%Y-%m")
        months.setdefault(key, []).append(dt)
        details.setdefault(key, []).append({
            "date": pr["closedDate"],
            "repo": pr.get("repository", {}).get("name", ""),
            "pr_id": pr.get("pullRequestId"),
            "title": pr.get("title", ""),
        })

    monthly = {}
    for key in sorted(months):
        year, month = map(int, key.split("-"))
        days_in_month = calendar.monthrange(year, month)[1]
        count = len(months[key])
        days_per_dep = days_in_month / count if count else None
        monthly[key] = {"count": count, "days_per_dep": days_per_dep}

    total_days = 180
    total_merged = len(merged)
    overall = total_days / total_merged if total_merged else None
    return {"monthly": monthly, "overall_days_per_dep": overall, "total": total_merged, "_details": details}


async def compute_pr_lead_times_by_month(
    client: httpx.AsyncClient, org: str, project: str, prs: list[dict], pat: str
) -> dict[str, dict]:
    """Lead time = closedDate - earliest commit date in the PR."""
    merged = [pr for pr in prs if pr.get("status") == "completed" and pr.get("closedDate")]
    sample = merged[:200]
    lead_times_by_month: dict[str, list[float]] = {}

    details: dict[str, list[dict]] = {}

    for pr in sample:
        repo_id = pr.get("repository", {}).get("id")
        pr_id = pr.get("pullRequestId")
        if not repo_id or not pr_id:
            continue
        commits = await fetch_pr_commits(client, org, project, repo_id, pr_id, pat)
        if not commits:
            continue
        commit_dates = [parse_dt(c.get("author", {}).get("date")) for c in commits]
        commit_dates = [d for d in commit_dates if d is not None]
        if not commit_dates:
            continue
        earliest_commit = min(commit_dates)
        closed_date = parse_dt(pr["closedDate"])
        if not closed_date:
            continue
        delta = (closed_date - earliest_commit).total_seconds()
        if delta >= 0:
            mk = closed_date.strftime("%Y-%m")
            lead_times_by_month.setdefault(mk, []).append(delta)
            details.setdefault(mk, []).append({
                "commit_date": earliest_commit.isoformat(),
                "finish_date": pr["closedDate"],
                "lead_time_hours": round(delta / 3600, 2),
                "repo": pr.get("repository", {}).get("name", ""),
                "pr_id": pr_id,
                "title": pr.get("title", ""),
            })

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
    result["_details"] = details
    return result


# ---------------------------------------------------------------------------
# Classification & formatting
# ---------------------------------------------------------------------------

def classify_dora(metric: str, value: float | None) -> str:
    """Return DORA performance category."""
    if value is None:
        return "N/A"
    if metric == "deploy_freq":
        if value <= 1:
            return "Elite"
        if value <= 7:
            return "High"
        if value <= 30:
            return "Medium"
        return "Low"
    if metric == "lead_time":
        if value < 24:
            return "Elite"
        if value < 24 * 7:
            return "High"
        if value < 24 * 30:
            return "Medium"
        return "Low"
    if metric == "cfr":
        if value <= 5:
            return "Elite"
        if value <= 10:
            return "High"
        if value <= 15:
            return "Medium"
        return "Low"
    if metric == "mttr":
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
