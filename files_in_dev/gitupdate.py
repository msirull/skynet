import subprocess, git

def update():
	if 'commits' in rmsg and rmsg["commits"] > 0:
		fbranch = rmsg["ref"]
		branch = fbranch.replace("refs/heads/", "")
		repo = rmsg["repository"]["name"]
		if branch == ptags["branch"] and repo == ptags["repo"]:
			msg = {"repo": repo, "branch": branch}
			print msg
			# Start update process
			currenttime=str(int(time.time()))
			print "starting update process at..."
			subprocess.call('rm -rf '+ work_dir, shell=True)
			subprocess.call('git clone git@github.com:msirull/'+ repo +'.git '+ work_dir, shell=True)
			# Insert compile scripts here
			# Stop Services...the services need to not be hard coded
			print "stopping services..."
			for s in services:
				subprocess.call('sudo service ' + s + ' stop', shell=True)
				# Moving/Archiving data
				print "archiving data"
				subprocess.call('mkdir /etc/backup/'+ currenttime, shell=True)
				subprocess.call('mv '+ webroot+'*' ' /etc/backup/'+ currenttime, shell=True)
				# Copy new data in
				print "copying new data in"
				subprocess.call('cp -r '+ work_dir +'* ' + webroot, shell=True)
				print "updating config"
				# Get an up-to-date config file
				subprocess.call('/etc/config/config_dl.sh /etc/config', shell=True)
				print "starting services"
				# Get everything working again
				for s in services:
					subprocess.call('service ' + s + ' start', shell=True)
					print "update done!"
		else:
			return "the branch or repo doesn't match, this one's not for me"
	else:
		return "nothing to do, there's no commits"
