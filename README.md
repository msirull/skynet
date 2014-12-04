skynet
======
AWS Autonomous...going beyond automation

Basic Concepts:
- Stacks autoupdate from Github webhooks
  - The first instance to receive the notification prepares the code (compiles, if necssary, and copies to S3)
  - If it updates successfully, it pushes the code to S3 and notifies the rest of the instances in its maintenance group
  - The rest of the instances "take a ticket" by posting to a maintenance queue and update when their "number comes up"
  - Deployment stops when an instance fails to update

Hard-Coded Settings (things I've done not flexible, just FYI):
- Local config files go in /etc/config
- Skynet installs to /etc/skynet/skynet-master (based on CloudFormation template)

Assumptions (things you have to do):
- An S3 config bucket that has 3 directories: Global, Environments, Layers
  - Global: What it sounds like
  - Environments: Things like DB passwords, logging settings, etc. with sub-directories by environment
  - Layers: Things universal to all environments of a layer (like service settings, Git SSH keys, etc) with sub-directories by layer
- Create a (blank) DynamoDB "endpoints" table with "env" and "layer" as the hash/key. This isn't in Cloudformation because (for now) this table is used for all environments. I suppose it doesn't have to be this way.

- You're using Github, have set up your repo with a deployment key, and put that key in the appropriate S3 location (see above). If it has the correct extension (.pem), it should get moved into the right spot.

Notes:
- There's a similar structure as the S3 config folder structure in DynamoDB tables for configuration info. This is the preferred location over S3 json files. You'll have better control over the config information your developers will have access to, and it will be easier for them to make updates.
- The Github SSH cloning is an unfortunate hack. The preferred method will be AWS CodeCommit when it is released (if for no other reason than because of IAM roles)
- All CloudFormation templates are built around a public Edge/Firewall/Reverse Proxy ASG connected to your App's private ASG, because...that's the way it's supposed to work. If you don't want to do any additional work around that, simply use the provided Nginx configs that do basic proxying.
