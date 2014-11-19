#!/bin/bash
iid=`curl -s http://169.254.169.254/latest/meta-data/instance-id`
jtags=`aws ec2 describe-tags --region us-west-2 --filter "Name=resource-id,Values=$iid"`
ltags=${jtags,,}
tags=$(echo $ltags | jq '.tags | from_entries')
echo $tags >> /etc/config/tags.info
branch=`echo $tags | jq -r '.branch'`
repo=`echo $tags | jq -r '.repo'`
dir="/etc/app/"
git config —global user.name "$iid"
git config —global user.email "support@cloudnineit.com"
git clone git@github.com:msirull/$repo.git $dir
#git pull git@github.com:msirull/$repo.git $dir
cp $dir* /var/www/html/
