iid=`curl -s http://169.254.169.254/latest/meta-data/instance-id`
jtags=`aws ec2 describe-tags --filter "Name=resource-id,Values=$iid"`
ltags=${jtags,,}
tags=$(echo $ltags | jq '.tags | from_entries')
branch=`echo $tags | jq -r '.branch'`
repo=`echo $tags | jq -r ‘.repo’`

dir= "/etc/app/"
gitssh= "/etc/config/git_ssh.pem"
git config —global user.name "$iid"
git config —global user.email "support@cloudnineit.com"
git init $dir
ssh-agent bash -c 'ssh-add $gitssh; git clone git@github.com:msirull/$repo.git $dir’
#ssh-agent bash -c 'ssh-add $gitssh; git pull git@github.com:msirull/$repo.git $dir’
mv $dir* /var/www/html/
