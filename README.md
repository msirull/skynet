skynet
======

Making AWS Autonomous

Assumptions/Hard-coded Settings
- Local config files go in /etc/config
- The S3 config bucket has 3 directories: Global, Environments, Layers
  - Global: What it sounds like
  - Environments: Things like DB passwords, logging settings, etc.
  - Layers: Things universal to all environments of a layer (like service settings, Git SSH keys, etc)
- There's a similar structure in the DynamoDB tables for configuration info. This is the preferred location over S3 json files. You'll have better control over the config information your developers will have access to, and it will be easier for them to make updates.
- You're using Github, have set up your repo with a deployment key, and put that key in the appropriate S3 location (see above). If it has the correct extension (.pem), it should get moved into the right spot.
- The Github SSH cloning is an unfortunate hack. The preferred method will be AWS CodeCommit when it is released (if for no other reason than because of IAM roles)
- All CloudFormation templates are built behind a public Edge ASG connected to your App's private ASG, because...that's the way it's supposed to work.
