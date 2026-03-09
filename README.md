# DORA Explorer

A CLI tool that extracts [DORA metrics](https://dora.dev/) from Azure DevOps projects by analyzing pipeline builds and pull requests over the past 6 months.

## Metrics

| Metric | Description |
|---|---|
| **Deployment Frequency** | How often changes reach production |
| **Lead Time for Changes** | Time from commit to deployment |
| **Change Failure Rate** | Percentage of deployments that fail |
| **Mean Time to Recovery** | Time to restore service after a failure |

## Prerequisites

- Python 3.12+
- An Azure DevOps Personal Access Token (PAT) with **read** access to builds, pipelines, repos, and pull requests

## Setup

1. **Clone the repository**

   ```bash
   git clone git@github.com:juanflorez/DORA_Explorer.git
   cd DORA_Explorer
   ```

2. **Create a virtual environment and install dependencies**

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install httpx openpyxl matplotlib
   ```

3. **Store your Azure DevOps PAT**

   Create a file called `env.tks` in the project root containing your Personal Access Token (plain text, single line):

   ```bash
   echo "your-pat-token-here" > env.tks
   ```

   This file is listed in `.gitignore` and will not be committed.

## Usage

```bash
source .venv/bin/activate
python dora_cli.py
```

The tool will prompt you for:
1. **Organization** — your Azure DevOps org name or URL
2. **Project** — which project to analyze (or all)
3. **Mode** — `pipelines` (build deployments) or `pullrequests` (merged PRs)

You can also pass arguments directly:

```bash
python dora_cli.py -org "https://myorg.visualstudio.com" -project "MyProject" -mode pipelines
```

### Output

After displaying the metrics table, the tool:
- Exports a **JSON report** to `reports/`
- Exports an **Excel report** (using the `DORA_DB_v4.xlsx` template) to `reports/`
- Offers an **interactive drill-down** into any cell (e.g. `df 2026-01` to see individual deployments for that month)

### Drill-down commands

```
df 2026-01    # Deployment Frequency details
lt 2026-01    # Lead Time details
cfr 2026-01   # Change Failure Rate details
mttr 2026-01  # MTTR recovery incidents
q             # Quit
```

## Charts from a manually populated Excel

If you collect DORA metrics manually (without Azure DevOps access), use
`chart_from_excel.py` to generate the same branded PNG charts directly from
a spreadsheet.

### Template

Use **`DORA_DB_GeneratorV3.xlsx`** as your starting point. It contains a sheet
called `TEAM_NAME_Manual` — copy and rename it for each team you want to track.
The part of the sheet name **before** `_Manual` becomes the team name on the
chart (e.g. `ZULU_Manual` → *ZULU*).

### How to fill in the `_Manual` sheet

Columns A–E are fixed (labels and auto-calculated totals — do not edit them).
**Enter your data from column F onwards**, one column per measurement period
(typically one month).

| Row | What to enter | Unit / notes |
|-----|---------------|--------------|
| 1 | Date of measurement | Pre-filled as 1st of each month — verify the year is correct |
| 2 | Successful releases to **ACC** (acceptance/staging) since last measurement | Count |
| 3 | Successful releases to **PROD** since last measurement | Count |
| 4 | **Failed** releases to PROD since last measurement | Count |
| 5 | Average time from commit to production | **Days** (e.g. `0.5` = 12 hours) |
| 6 | Average time to recover from important failures | **Days** (e.g. `1.5` = 36 hours) |

**Tips:**
- Leave future months as `0` — the script ignores them automatically.
- The chart always shows the **last 6 non-future months** with at least one non-zero value.
- Dates in row 1 must be in chronological order. A wrong year (e.g. `2025-03` where `2026-03` was intended) will trigger a warning and that column will be skipped.
- CFR is derived automatically as `failed / (succeeded + failed) × 100` — do not enter a percentage.

### Running

```bash
source .venv/bin/activate
python chart_from_excel.py path/to/your-workbook.xlsx
```

The PNG chart is saved **in the same folder as the Excel file**, named
`DORA_chart_<TEAM>_manual_<timestamp>.png`. A workbook with multiple
`_Manual` sheets produces one chart per sheet.

## Project Structure

```
dora_cli.py          CLI entry point — prompts, table output, export, drill-down
dora_metrics.py      DORA metric computation (pipeline and PR modes)
dora_charts.py       Chart generation module (used by both CLI and Excel script)
chart_from_excel.py  Generate charts from a manually populated Excel workbook
azure_api.py         Azure DevOps REST API client (read-only)
DORA_DB_GeneratorV3.xlsx  Excel template — copy the _Manual sheet per team and fill in metrics
env.tks              Your Azure DevOps PAT (not committed)
reports/             Generated JSON and Excel reports (gitignored)
```
