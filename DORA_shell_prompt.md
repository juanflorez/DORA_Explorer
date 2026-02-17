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
