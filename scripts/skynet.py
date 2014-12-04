from flask import Flask, request

from boto.sqs.message import RawMessage
from boto.utils import get_instance_metadata
import boto.sqs, boto.ec2, urllib2, git, subprocess, shutil, time, json, datetime, hmac
from hashlib import sha1
from boto.s3.connection import S3Connection

app = Flask(__name__)
iid = get_instance_metadata()['instance-id']
tags = file.read(open("/etc/config/tags.info", "r"))
ptags = json.loads(tags)
region='us-west-2'
region = get_instance_metadata()['placement']['availability-zone'][:-1]
ec2_conn = boto.ec2.connect_to_region(region)
sqs_conn = boto.sqs.connect_to_region(region)
s3_conn = S3Connection()

skynet_source="https://raw.githubusercontent.com/msirull/skynet/master/scripts/skynet.py"
reservations = ec2_conn.get_all_instances(filters={"tag:maintenance-group" : ptags["maintenance-group"]})
instances = [i for r in reservations for i in r.instances]
ips = [i.ip_address for i in instances]
q = sqs_conn.get_queue(ptags['maintenance-group']+'-maint')
m = RawMessage()
msg_src = ""
msg_type = ""
work_dir="/etc/app/"
services = ["nginx", "php-fpm-5.5"]
webroot="/var/www/html/"
repo_bucket="repo-staging"
gittoken='w3rQ2Q4KK7Wm73ANqg' #I know I need to move this

@app.route('/update', methods = ['POST'])
def ext_inbound():
	# Store request
	rmsg = json.loads(request.data)
	# Only move forward if there's a commit
	msg=request.data
	# Decode
	jmsg = json.dumps(msg)		
	print(jmsg)
	headers = request.headers
	print headers
	# Validate sender
	# What's the message say to do?
	if 'action' in rmsg and rmsg['action'] == 'config-update':
		subprocess.call('/etc/config/config_dl.sh /etc/config', shell=True)
		return "Config Updated!"
	if 'action' in rmsg and rmsg['action'] == 'skynet-update':
		f = urllib2.urlopen(skynet_source)
		ff=open("/etc/config/skynet.py", "w")
		ff.write(f.read())
		ff.close()
		shutil.copy('/etc/config/skynet.py', '/etc/config/skynet_main.py')
		return "Assimilation Successful"
	if 'User-Agent' in headers and headers['User-Agent'].startswith('GitHub-Hookshot'):
		print "OK you *say* you're from Github"
		if 'X-Hub-Signature' in headers:
			signature = "sha1="+hmac.new(gittoken, request.data, sha1).hexdigest()
			print signature
			if headers['X-Hub-Signature'] == signature:
				print "Github Identity Confirmed"
				if 'commits' in rmsg and rmsg["commits"] > 0:
					fbranch = rmsg["ref"]
					branch = fbranch.replace("refs/heads/", "")
					repo = rmsg["repository"]["name"]
					if branch == ptags["branch"] and repo == ptags["repo"]:
						msg = {"repo": repo, "branch": branch}
						# Start update process
						currenttime=str(int(time.time()))
						regulartime=(datetime.datetime.fromtimestamp(int(currenttime)).strftime('%Y-%m-%d %H:%M:%S'))
						print "starting update process at "+regulartime
						subprocess.call('rm -rf '+ work_dir, shell=True)
						subprocess.call('git clone git@github.com:msirull/'+ repo +'.git '+ work_dir, shell=True)
						# Insert compile scripts here
						# Stop Services...the services need to not be hard coded
						print "stopping services..."
						for s in services:
							subprocess.call('service ' + s + ' stop', shell=True)
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
						subprocess.call('aws s3 cp '+work_dir+' s3://'+repo_bucket+'/'+ptags["repo"]+'/'+ptags["branch"]+'/'+currenttime+' --recursive', shell=True)
						print "copy to s3 done!"
					else:
						return "the branch or repo doesn't match, this one's not for me"
				else:
					print "No commits"
					return "nothing to do, there's no commits"
			else:
				print "Access Denied - Hashes don't match"
				return "You don't know me"
		else:
			print "There's no Github Signature"
			return "I don't believe you"
	else:
		print "Not a recognized notification"
		return "I don't know what's going on here"
	# Encode message to go out
	jmsg = json.dumps(msg)
	# Notify maintenance group
	print "notifying the hoard"
	for ip in ips:
		url = "http://%s/notify" % ip
		def out_notify():			
			print url
			data = jmsg
			headers = { 'content-type' : 'application/json' }
			req = urllib2.Request(url, data, headers)
			print req
			response = urllib2.urlopen(req)
			print response.read()
	return 'success!'

@app.route('/notify', methods = ['POST'])
def in_notify():
	omsg = request.data
	rmsg = json.loads(request.data)
	# Get in line
	iid = "test inline iid"
	msg_src = "test inline message source"
	m.message_attributes = {
						"instance-id":{"data_type": "String", "string_value": iid},
						"message-source":{"data_type": "String", "string_value": msg_src}}
	m.set_body(omsg)
	q.write(m)
	return "Success iid"	

if __name__ == "__main__":
	app.run()
