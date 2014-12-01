skynet
======

Making AWS Autonomous

Assumptions/Hard-coded Settings
- Local config files go in /etc/config
- The S3 config bucket has 3 directories: Global, Environments, Layers
  - Global: What it sounds like
  - Environments: Things like DB passwords, logging settings, etc.
  - Layers: Things universal to all environments of a layer (like service settings, Git SSH keys, etc)
- There's a similar structure in the DynamoDB tables for configuration info that works in DynamoDB. This is the preferred location over S3 json files. You'll have better control over the config information your developers will be able to change and it will be easier for them to do so.
- You're using Github, have setup your repo with a deployment key, and put that key in the appropriate S3 location (see above)
- The Github SSH cloning is an unfortunate hack. The preferred method will be AWS CodeCommit, when it is released (because of IAM roles)
