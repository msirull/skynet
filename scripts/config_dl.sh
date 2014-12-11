#!/bin/sh
##Get Instance Tags
region=$(curl -s http://169.254.169.254/latest/meta-data/placement/availability-zone | sed s'/.$//')
iid=`curl -s http://169.254.169.254/latest/meta-data/instance-id`
jtags=`aws ec2 describe-tags --region $region --filter "Name=resource-id,Values=$iid"`
ltags=${jtags,,}
tags=$(echo $ltags | jq '.tags | from_entries')
rm /etc/config/tags.info
echo $tags >> /etc/config/tags.info

##Get IAM Role for Instance (Get full ARN and strip "arn..")
role=$(curl -s http://169.254.169.254/latest/meta-data/iam/security-credentials/)

##Get list of policies with "config"
policies=$(aws iam list-role-policies --role-name $role | jq .PolicyNames[] | jq -r 'if contains("config") == true then . else empty end')

##Get s3 config file paths (by getting policy docs, finding s3 Objects and stripping "arn..")
configfiles=$(for policy in $policies; do echo $(aws iam get-role-policy --role-name $role --policy-name $policy | jq -r '.PolicyDocument.Statement[] | if .Action[]=="s3:GetObject" then .Resource[] else empty end' |  sed -e 's/arn:aws:s3::://g' | sed -e 's/*//g'); done)

##Download all config files and combine into one file
rm -rf $1/*.json
for dl in $configfiles; do aws s3 cp --recursive s3://$dl $1/; done
jq -s 'add' $1/*.json > $1/rconfig.json

##Move SSL files into place
mv $1/*.crt /etc/ssl/
mv $1/*.key /etc/ssl
mv $1/*.pem /root/.ssh/
chmod 400 /root/.ssh/*.pem
chmod 644 /etc/ssl/*.key
chmod 644 /etc/ssl/*.crt
chmod 755 /etc/config/*.sh
