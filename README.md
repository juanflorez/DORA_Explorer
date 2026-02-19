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
   pip install httpx openpyxl
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
- Exports an **Excel report** (using the `DORA_DB_v3.xlsx` template) to `reports/`
- Offers an **interactive drill-down** into any cell (e.g. `df 2026-01` to see individual deployments for that month)

### Drill-down commands

```
df 2026-01    # Deployment Frequency details
lt 2026-01    # Lead Time details
cfr 2026-01   # Change Failure Rate details
mttr 2026-01  # MTTR recovery incidents
q             # Quit
```

## Project Structure

```
dora_cli.py          CLI entry point — prompts, table output, export, drill-down
dora_metrics.py      DORA metric computation (pipeline and PR modes)
azure_api.py         Azure DevOps REST API client (read-only)
DORA_DB_v3.xlsx      Excel template with formulas for auto-calculated metrics
env.tks              Your Azure DevOps PAT (not committed)
reports/             Generated JSON and Excel reports (gitignored)
```
