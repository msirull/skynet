#!/bin/bash
echo "Which AWS account do you have access to? dev/prod"
read aws
	if [ "$aws" == "dev" ]; then
	zoneapex=$(echo "dev.zoneapex.com")
	configbucket=$(echo "dev-templates-bucket");
elif [ "$aws" == "prod" ]; then
	zoneapex=$(echo "prod.zoneapex.com")
	configbucket=$(echo "prod-templates-bucket");
fi
echo "Enter a sub-domain: (not FQDN)"
read subdomain
echo "Enter Repo, must match Github *exactly*"
read repo
echo "Enter Branch, must match Github *exactly*"
read branch
echo "Use Cloudfront? y/n"
read use_cloudfront
echo "Do you need to create a new database? y/n"
read new_database
if [ "$new_database" == "y" ]; then
	echo "mysql or mongo?"
read db_type;
elif [ $new_database == "n" ]; then
		echo "Enter hostname/local IP address"
		read db_address
		echo "What type of DB is it? mysql or mongo?"
		read db_type
fi
echo "Call your stack something:"
read stack_name
echo "So domain is '"$subdomain"."$zoneapex"', repository is '"$repo"', branch is '"$branch"' and it's a '"$db_type"' database?
Is that right? y/n"
read ready
if [ "$ready" == "y" ]; then
	echo "Let's go!!!"
else echo "Ok, better luck next time"
exit
fi
if [ "$aws" == "dev" ]; then
	keypair=$(echo "dev")
elif [ "$aws" == "prod" ]; then
	keypair=$(echo "prod-deploy")
fi
if [ "$aws" == "prod" ]; then
	env=$(echo "prod")
else env=$(echo "$branch")
fi
version=$(echo "0.1")
mq=$(echo "$repo-$env-maint")
aws cloudformation create-stack --stack-name "$stack_name" --template-url http://"$configbucket".s3.amazonaws.com/elb-asg-php-nginx-cloudformation.json --parameters ParameterKey=Repo,ParameterValue="$repo",UsePreviousValue=false ParameterKey=KeyName,ParameterValue="$keypair",UsePreviousValue=false ParameterKey=ZoneApex,ParameterValue="$zoneapex",UsePreviousValue=false ParameterKey=SubDomain,ParameterValue="$subdomain",UsePreviousValue=false ParameterKey=Branch,ParameterValue="$branch",UsePreviousValue=false ParameterKey=Environment,ParameterValue="$env",UsePreviousValue=false --tags Key="Name",Value="$repo-$env" Key="repo",Value="$repo" Key="branch",Value="$branch" Key="version",Value="1.0" Key="maintenance-queue",Value="$mq" Key="layer",Value="$repo" Key="environment",Value="$env"

