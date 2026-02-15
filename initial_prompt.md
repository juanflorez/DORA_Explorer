A webapp that help teams to track their DORA metrics,  from their Microsoft Azure Devops deployment pipelines.

The website will ask the user the following information:

Az token: Used for the tool to be authorized to get the information it needs.
Project: The project the tool needs to analyse
Git repo: In case of multiple repos, select the one that should be analysed
Deployment environment: the endpoint where the measurements will be taken


once the info is collected, the tool should use Azure Devops API to query how many deployments where created in the past 6 months, and display that information.
