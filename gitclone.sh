dir=/etc/app/
gitssh=/etc/config/gitssh.pem
repo=comes_from_tag
branch=comes_from_tag
git config —global user.name “iid”
git config —global user.email “support@cloudnineit.com”
git init dir
ssh-agent bash -c 'ssh-add gitssh; git clone git@github.com:msirull/repo.git dir’
#ssh-agent bash -c 'ssh-add gitssh; git pull git@github.com:msirull/repo.git dir’
