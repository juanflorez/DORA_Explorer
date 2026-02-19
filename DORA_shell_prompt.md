These are the inhouse DORA metrics, and should be taken for the past 6 months if possible:

Deployment Frequency​​:
This metric measures how often a team inserts changes in acceptance and production​​. 
A higher deployment frequency generally indicates faster delivery and greater agility. ​​ 

Lead Time for Changes​​:
This metric measures the average time it takes for a code change to go
from commit by developers, to being in production. ​
Shorter lead times indicate faster responsiveness to market changes. ​

Change Failure Rate:
This metric measures the percentage of deployments that result in failures in production. ​​
A lower change failure rate signifies better stability and reliability.​

Mean Time to Recovery (MTTR)​:
This metric measures the average time it takes to restore service after a
failure in production. Usually it starts counting from the time the failure (bug) is reported, until the fix is available in Production.
Shorter MTTRs indicate faster recovery times and less downtime. 


The tool written in Python  will analize the environments and code repos of an specific project in Microsoft AzureDevops in order to extract our inhouse DORA metrics.
To connect to AzureDevops, it will ask for the AZ project, and then collect the info using the token stored in a file called env.tks
The tool should use the access token only to read, it should not write  nor modify any data in the azure devops project.

No need for a fancy UI at the begining.
A simple tool that works in the command prompt terminal should be enough for version 1

## Pull Request Mode (v7)

In some projects, it is better to measure the frequency of approved pull requests instead of the deployment on the pipeline. So, after asking the project, ask if the tool should take the DORA metrics using pipelines or pull requests. If it is pipelines, keep operating as is, but if it is pull requests, then find all the repos that were active in the past 6 months, and calculate the DORA metrics using the time of the approval of pull requests and the amount of approved pull requests instead of the deployment times in the pipelines.

### DORA Metrics mapping for Pull Request mode

| Metric | Pipeline Mode | Pull Request Mode |
|---|---|---|
| **Deployment Frequency** | Days between successful pipeline deployments | Days between approved pull requests |
| **Lead Time for Changes** | Time from commit to build finish | Time from first commit in PR to PR approval |
| **Change Failure Rate** | Failed builds / total builds | PRs whose associated pipeline build failed after merge / total merged PRs |
| **MTTR** | Time from failed build to next successful build | Time from failed post-merge build to next successful build (on same pipeline) |

## Excel Export — DORA_DB template

There is an Excel file `DORA_DB.xlsx` in the project root that serves as the official reporting template. It has 4 tabs with Excel Table objects and formulas that auto-calculate the DORA metrics. The next version of the tool should produce a **copy** of this file (never overwrite the original), populated with data from the current run.

### Tab structure

**Deployments** (Excel Table: `Deployments`)
| Column | Description |
|---|---|
| `DeploymentID` | Sequential integer |
| `Acc` | Date deployed to acceptance (= build finish date) |
| `Prod` | Date deployed to production (= build finish date; same as Acc for pipeline mode) |
| `failed?` | 1 if the build failed/partiallySucceeded, 0 otherwise |

In pipeline mode, each build with a result of succeeded/failed/partiallySucceeded becomes a row. `Acc` and `Prod` both use the build's `finishTime` (date only). In PR mode, each merged PR becomes a row using its `closedDate`.

**Commits** (Excel Table: `Commits`)
| Column | Description |
|---|---|
| `commit id` | Integer (build ID or PR ID) |
| `DateCommit` | The commit/author date (date only) |
| `DeploymentID` | FK to `Deployments.DeploymentID` |
| `DaysToRelease` | Integer — days from commit to deployment (`Prod - DateCommit`) |

In pipeline mode, each lead-time detail record becomes a row. In PR mode, each PR lead-time detail record becomes a row.

**Issues** (Excel Table: `Issues`)
| Column | Description |
|---|---|
| `Issue ID` | Integer (sequential) |
| `Report Date` | The failure date (date only) |
| `Fixed-ReleaseID` | FK to `Deployments.DeploymentID` of the recovery build |
| `DaysToRelease` | Integer — days from failure report to recovery |
| `ReleaseDate` | Date of the recovery deployment (date only) |

Each MTTR detail record (recovery incident) becomes a row.

**DORA** (calculation tab — do NOT modify)
Contains formulas referencing the three data tables above (COUNTIFS, SUMIFS, AVERAGEIFS over monthly date ranges). Row 1 has month-start dates; rows 2–6 compute Deployment Frequency (ACC & PROD), Failure Rate, Cycle Time, and MTTR. These formulas auto-recalculate when the data tabs are populated.

### Implementation notes

- Use `openpyxl` to open the template, populate the three data tabs, and save a copy.
- The copy should go into `reports/` with naming: `DORA_DB_<project>_<mode>_<YYYYMMDD_HHMMSS>.xlsx`.
- Update the month-start dates in row 1 of the DORA tab to match the 6-month window of the current run.
- Preserve all formulas in the DORA tab — only write data to Deployments, Commits, and Issues.
- Resize the Excel Tables to match the number of data rows so formulas pick up the new data.
- The `DaysToRelease` column in Commits can be a formula (`=Deployments[Prod]-[@DateCommit]`) or a computed integer — either works since the DORA tab references the column by name.
