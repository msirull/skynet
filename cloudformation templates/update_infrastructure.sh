subdomain="testeast1"
zoneapex="cloudnineit.net"
configbucket="test-cf-templates"
keypair="easttest"
privaterepo="test"
publicrepo="edge"
branch="master"
env="prod"
stack_name="TestEast1"
aregion="us-east-1"
version=$(echo "1.0")
mq=$(echo "$repo-$env-maint")
aws s3 cp /Users/Me/Repos/skynet/cloudformation\ templates/php-nginx.json s3://$configbucket --profile test
aws cloudformation create-stack --profile test --region "$aregion" --stack-name "$stack_name" --capabilities "CAPABILITY_IAM" --template-url https://s3.amazonaws.com/"$configbucket"/php-nginx.json --parameters ParameterKey=PublicRepo,ParameterValue="$publicrepo",UsePreviousValue=false ParameterKey=PrivateRepo,ParameterValue="$privaterepo",UsePreviousValue=false ParameterKey=KeyPair,ParameterValue="$keypair",UsePreviousValue=false ParameterKey=ZoneApex,ParameterValue="$zoneapex",UsePreviousValue=false ParameterKey=SubDomain,ParameterValue="$subdomain",UsePreviousValue=false ParameterKey=Branch,ParameterValue="$branch",UsePreviousValue=false ParameterKey=Environment,ParameterValue="$env",UsePreviousValue=false