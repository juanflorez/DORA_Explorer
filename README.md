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
   pip install -r requirements.txt
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

Use **`DORA_DB_GeneratorV4.xlsx`** as your starting point. Make a copy of the
file for each team (or keep multiple teams in one file using multiple sheets —
see below).

### Two ways to populate the workbook

#### Option A — Detailed tracking (Deployments, Commits, Issues tabs)

Fill in the raw event data in the three source tabs:

- **Deployments** — one row per deployment: date and whether it failed
- **Commits** — one row per commit: commit date and which deployment it belonged to
- **Issues** — one row per production incident: date reported and which deployment fixed it

The **DORA** tab calculates the four metrics automatically from this data.

#### Option B — Lightweight manual entry (`_Manual` tab)

1. **Rename the sheet** from `TEAM_NAME_Manual` to `<YourTeam>_Manual`
   (e.g. `ZULU_Manual`). The part before `_Manual` becomes the team name on the chart.

2. **Fill in the yellow-highlighted cells F1 to K6** — one column per measurement
   period (typically one month):

   | Cell | What to enter | Unit / notes |
   |------|---------------|--------------|
   | Row 1 | Date of measurement | Pre-filled as 1st of each month — check the year |
   | Row 2 | Successful releases to **ACC** (staging) since last measurement | Count |
   | Row 3 | Successful releases to **PROD** since last measurement | Count |
   | Row 4 | **Failed** releases to PROD since last measurement | Count |
   | Row 5 | Average time from commit to production | **Days** (e.g. `0.5` = 12 h) |
   | Row 6 | Average time to recover from important failures | **Days** (e.g. `1.5` = 36 h) |

   **Tips:**
   - Do not edit columns A–E (labels and auto-calculated summaries).
   - Leave future months as `0` — the script skips them automatically.
   - Dates in row 1 must be chronological. A wrong year triggers a warning and that column is skipped.
   - CFR is derived automatically as `failed / (succeeded + failed) × 100`.

### Generating the chart

```bash
source .venv/bin/activate
python chart_from_excel.py path/to/your-workbook.xlsx
```

The script reads every sheet whose name ends with `_Manual`, generates one PNG
per sheet, and saves it **in the same folder as the Excel file**:
`DORA_chart_<TEAM>_manual_<timestamp>.png`.

The chart always covers the **last 6 non-future months** that contain at least one non-zero value.

## Project Structure

```
dora_cli.py          CLI entry point — prompts, table output, export, drill-down
dora_metrics.py      DORA metric computation (pipeline and PR modes)
dora_charts.py       Chart generation module (used by both CLI and Excel script)
chart_from_excel.py  Generate charts from a manually populated Excel workbook
azure_api.py         Azure DevOps REST API client (read-only)
DORA_DB_GeneratorV4.xlsx  Excel template — fill in source tabs or use the _Manual sheet
env.tks              Your Azure DevOps PAT (not committed)
reports/             Generated JSON and Excel reports (gitignored)
```
