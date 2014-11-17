dir=workingdir
git config —global user.name “iid”
git config —global user.email “support@cloudnineit.com”
git init dir
ssh-agent bash -c 'ssh-add ~/Dropbox/Work\ Files/repos/skynet/git_ssh.pem; git clone git@github.com:msirull/skynet.git dir’
