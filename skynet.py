from flask import Flask, request, json
from boto.sqs.message import RawMessage
from boto.utils import get_instance_metadata
import boto.sqs, boto.ec2, urllib2, git, subprocess, shutil, time

app = Flask(__name__)
iid = get_instance_metadata()['instance-id']
tags = file.read(open("/etc/config/tags.info", "r"))
ptags = json.loads(tags)
ec2_conn = boto.ec2.connect_to_region('us-west-2')
sqs_conn = boto.sqs.connect_to_region("us-west-2")

reservations = ec2_conn.get_all_instances(filters={"tag:maintenance-group" : ptags["maintenance-group"]})
instances = [i for r in reservations for i in r.instances]
ips = [i.ip_address for i in instances]
q = sqs_conn.create_queue('test-prod-maint')
m = RawMessage()
msg_src = []
msg_type = []
#iid = ["i-9eba6394"]
work_dir="/etc/app/"
services = ["nginx", "php-fpm-5.5"]
webroot="/var/www/html/"

@app.route('/update', methods = ['POST'])
def ext_inbound():
	# Store request
	rmsg = json.loads(request.data)	
	# Validate sender
	# What's the message say to do?
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
			return "go away, the branch or repo doesn't match"
	else:
		return "go away, there's no commits"
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
	# Validate sender
	if request.method == 'POST' and rmsg["Type"] == "Notification" :
		msg = rmsg["Message"]
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
	app.run(debug=True, port=666, host='0.0.0.0')
