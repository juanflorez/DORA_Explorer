#!/usr/bin/env python3
"""
Generate deterministic mock Azure DevOps build data for the four test teams.

Profiles (based on real elia-digitization projects):
  Alpha   → Panoptic  : Elite DF, Low CFR (38%) ← WEAKNESS
  Bravo   → Nova      : Medium DF, Low Lead Time (15-25d) ← WEAKNESS
  Charlie → EL.AI     : Elite DF, Poor MTTR (2-5d) ← WEAKNESS
  Delta   → Lighthouse: Low DF (one deploy/month) ← WEAKNESS

Run:  python tests/generate_mock_data.py
Output: tests/mock_data/<team>_team.json
"""

import json
import random
from datetime import datetime, timedelta, UTC
from pathlib import Path

random.seed(2025)

START = datetime(2025, 9, 1, tzinfo=UTC)
END   = datetime(2026, 2, 28, 23, 59, 59, tzinfo=UTC)


def iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def gen_builds(
    name: str,
    pipeline_id: int,
    interval_hrs: float,          # avg hours between builds
    failure_rate: float,           # 0-1
    lt_hrs_range: tuple,           # (min, max) lead time hours commit→deploy
    recovery_hrs_range: tuple,     # (min, max) hours from failure to next success
) -> tuple[list[dict], dict[str, str]]:
    """
    Generate a list of Azure DevOps-shaped build records and a commit lookup dict.

    After a failure, the next successful build is delayed by recovery_hrs_range
    so that MTTR is controlled independently of the normal deployment interval.
    """
    builds: list[dict] = []
    commits: dict[str, str] = {}
    bid = pipeline_id * 1000

    t = START + timedelta(hours=random.uniform(0, interval_hrs * 0.5))
    recovering_until: datetime | None = None

    while t <= END:
        # If we're mid-incident, skip forward to the recovery point
        if recovering_until is not None:
            if t < recovering_until:
                t = recovering_until
            result = "succeeded"
            recovering_until = None
        else:
            failed = random.random() < failure_rate
            result = "failed" if failed else "succeeded"
            if failed:
                recovering_until = t + timedelta(
                    hours=random.uniform(*recovery_hrs_range)
                )

        src = f"sha{bid:010d}"
        lt  = random.uniform(*lt_hrs_range)

        builds.append({
            "id":     bid,
            "result": result,
            "status": "completed",
            "finishTime":    iso(t),
            "sourceVersion": src,
            "definition": {"id": pipeline_id, "name": f"{name}-ci"},
            "repository": {
                "id":   f"repo-{name.lower()}",
                "name": f"{name.lower()}-app",
            },
            "project": {
                "id":   f"proj-{name.lower()}",
                "name": f"{name} Team",
            },
        })
        commits[src] = iso(t - timedelta(hours=lt))

        bid += 1
        t += timedelta(hours=random.uniform(interval_hrs * 0.7, interval_hrs * 1.3))

    return builds, commits


# ── Team profiles ──────────────────────────────────────────────────────────────
#
# Alpha (Panoptic) — Elite frequency, HIGH failure rate
#   DF:   Elite  (~0.3 days/deploy, build every 7h)
#   LT:   High   (8–24h)
#   CFR:  LOW    (38%) ← WEAKNESS
#   MTTR: High   (1–4h, quick recovery but happens a lot)
#
# Bravo (Nova) — Medium frequency, very long lead times
#   DF:   Medium (every 10–15 days)
#   LT:   LOW    (15–25 days = 360–600h) ← WEAKNESS
#   CFR:  High   (10%)
#   MTTR: Elite  (0.5–2h, fixes fast when they do break)
#
# Charlie (EL.AI) — Elite frequency, slow incident recovery
#   DF:   Elite  (~0.4 days/deploy, build every 9h)
#   LT:   Elite  (2–12h)
#   CFR:  Medium (22%)
#   MTTR: LOW    (2–5 days = 48–120h) ← WEAKNESS: incidents drag on
#
# Delta (Lighthouse) — Almost never deploys
#   DF:   LOW    (one deploy every 25–40 days) ← WEAKNESS
#   LT:   Medium (10–20 days = 240–480h)
#   CFR:  Low    (30%)
#   MTTR: Medium (18–48h)
# ──────────────────────────────────────────────────────────────────────────────

TEAMS = [
    dict(
        name="Alpha",
        pipeline_id=1,
        interval_hrs=7,
        failure_rate=0.38,
        lt_hrs_range=(8, 24),
        recovery_hrs_range=(1, 4),
        weakness="Change Failure Rate (38%) — too many broken builds reaching production.",
        improve="Introduce mandatory PR review gates and automated regression tests "
                "before merging to reduce the proportion of failing pipeline runs.",
    ),
    dict(
        name="Bravo",
        pipeline_id=2,
        interval_hrs=270,
        failure_rate=0.10,
        lt_hrs_range=(360, 600),
        recovery_hrs_range=(1, 2),
        weakness="Lead Time for Changes (15–25 days) — commits take too long to reach production.",
        improve="Break large PRs into smaller increments and automate environment "
                "provisioning to cut the review-to-deploy pipeline from weeks to days.",
    ),
    dict(
        name="Charlie",
        pipeline_id=3,
        interval_hrs=9,
        failure_rate=0.22,
        lt_hrs_range=(2, 12),
        recovery_hrs_range=(48, 120),
        weakness="Mean Time to Recovery (2–5 days) — incidents take far too long to resolve.",
        improve="Establish on-call runbooks, automated rollback triggers, and feature "
                "flags so incidents can be contained within hours rather than days.",
    ),
    dict(
        name="Delta",
        pipeline_id=4,
        interval_hrs=780,
        failure_rate=0.30,
        lt_hrs_range=(240, 480),
        recovery_hrs_range=(18, 48),
        weakness="Deployment Frequency (one release every ~30 days) — releases are too infrequent.",
        improve="Adopt trunk-based development and continuous delivery practices to "
                "deploy smaller changes more frequently and reduce per-release risk.",
    ),
]


def main():
    out_dir = Path(__file__).parent / "mock_data"
    out_dir.mkdir(exist_ok=True)

    for team in TEAMS:
        name = team["name"]
        builds, commits = gen_builds(
            name=name,
            pipeline_id=team["pipeline_id"],
            interval_hrs=team["interval_hrs"],
            failure_rate=team["failure_rate"],
            lt_hrs_range=team["lt_hrs_range"],
            recovery_hrs_range=team["recovery_hrs_range"],
        )

        ok  = sum(1 for b in builds if b["result"] == "succeeded")
        bad = sum(1 for b in builds if b["result"] != "succeeded")

        payload = {
            "metadata": {
                "team":     f"{name} Team",
                "org":      "elia-digitization",
                "mode":     "pipelines",
                "months":   ["2025-09","2025-10","2025-11","2025-12","2026-01","2026-02"],
                "weakness": team["weakness"],
                "improve":  team["improve"],
                "stats": {
                    "total_builds":     len(builds),
                    "succeeded":        ok,
                    "failed":           bad,
                    "cfr_approx_pct":   round(bad / len(builds) * 100, 1) if builds else 0,
                    "df_approx_days":   round(180 / ok, 1) if ok else None,
                },
            },
            "builds":  builds,
            "commits": commits,
        }

        path = out_dir / f"{name.lower()}_team.json"
        path.write_text(json.dumps(payload, indent=2))

        print(f"  {name} Team → {path.name}")
        print(f"    builds={len(builds)}, ok={ok}, fail={bad}, "
              f"CFR≈{payload['metadata']['stats']['cfr_approx_pct']}%, "
              f"DF≈{payload['metadata']['stats']['df_approx_days']}d/dep")
        print(f"    weakness: {team['weakness']}")


if __name__ == "__main__":
    print("Generating mock data...\n")
    main()
    print("\nDone.")
