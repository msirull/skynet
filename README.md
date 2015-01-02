skynet
======
AWS Autonomy...going beyond automation

Note: While this is feature complete, this is still in testing and has a few assumptions about my environment. If you're interested in trying it out, just shoot me an email at dev at sirull dot com. Thanks!

Basic Concepts:
- Servers talk to each other to coordinate operations including: code updates, config updates, service registration, etc.
- Stacks autoupdate from Github webhooks
  - The first instance to receive the notification prepares the code (compiles, if necssary, and copies to S3)
  - If it updates successfully, it pushes the code to S3 and notifies the rest of the instances in its maintenance group
  - The rest of the instances "take a ticket" by posting to a maintenance queue and update when their "number comes up"
  - Deployment stops when an instance fails to update

Benefits:
- Decentrialized "management"
- Self-maintaining clusters
- Complete Layer isolation. No need to expose cluster to a deployment server or open vulnerable ports (22) to update servers
- More rapid updates vs AMI rollouts and more cost effective, especially at scale (not paying for partial hours every update)
- CodeDeploy requires every instance to compile its own code (I think) and uses long polling. Skynet uses push

The included CloudFormation template "php-nginx" does the following:
- Creates 2 layers: A public Reverse Proxy layer and a private "API" layer
- The Private layer is fully ready to run PHP 5.5 compatible code with Nginx and PHP-FPM (see assumptions below)
- Creates a public Route 53 record pointing to the RP layer
- Layers register with DynamoDB (eventually will be distributed)
- The RP layer will automatically load the private endpoints (from a DynamoDB endpoints table, see assumptions below)
- Creates S3 config/repo buckets

This could be easily modified to support Node, Java, etc.

Getting Started:<br>
1) You'll need to have at least one domain in your AWS account. Just the hosted zone, nothing else.<br>
2) Create an "endpoints" table in the region you're deploying to with a hash and range of "env" - "layer"
3) Create a CloudFormation stack using the php-nginx.json template.<br>
4) It'll ask you for a few parameters. If you just want to see how it works, you can put anything into the "branch", "repo", and "env" fields. You'll just only have the phptest.php file in the web root. You don't even need a Key Pair if you don't want.<br>
- That's it! Give it a few minutes to get everything spun up and you should be able to go to: "subdomain.zoneapex/repo/env/phptest.php" (replace "repo" and "env" with the appropriate values)
- You can also test that Skynet is responding by sending a POST to URL:1666/repo/env/update with any JSON or URL:1666/update for the edge layer (replace "repo" and "env" with the appropriate values)

At this point, you haven't accomplished much more than a standard CF Template. However, Skynet *is* running now. So if you've put a real repo and branch in your parameters, you should be able to add your SSH key into the appropriate S3 location (see below), add the webook into Github, and be off to the races.

Please check the wiki for additional information as well as all commands Skynet accepts
