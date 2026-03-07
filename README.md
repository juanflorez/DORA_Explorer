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

### Workbook format

Use `reports/DORA_DB_Generator.xlsx` as your template. Each team needs a sheet
whose name ends with `_Manual` — the part before `_Manual` becomes the team
name on the chart (e.g. `ZULU_Manual` → *ZULU*).

Data columns start at **column F**. Row layout:

| Row | Content |
|-----|---------|
| 1 | Date of measurement (one column per period) |
| 2 | Releases to ACC since last measurement |
| 3 | Releases to PROD since last measurement |
| 4 | Failed releases to PROD (count) |
| 5 | Average lead time — days from commit to production |
| 6 | Average MTTR — days to recover from important failures |

The script automatically selects the **last 6 non-future months** and skips
columns that are entirely zero. Dates must be in chronological order; any
out-of-order date (e.g. a wrong year) triggers a warning and is skipped.

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
DORA_DB_v4.xlsx      Excel template with formulas for auto-calculated metrics
env.tks              Your Azure DevOps PAT (not committed)
reports/             Generated JSON and Excel reports (gitignored)
```
