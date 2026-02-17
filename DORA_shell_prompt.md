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
