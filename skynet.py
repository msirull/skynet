from flask import Flask, request, json
from boto.sqs.message import RawMessage
from boto.utils import get_instance_metadata
import boto.sqs, boto.ec2, urllib2, git, subprocess, shutil, time

app = Flask(__name__)

ec2_conn = boto.ec2.connect_to_region('us-west-2')
sqs_conn = boto.sqs.connect_to_region("us-west-2")

reservations = ec2_conn.get_all_instances(filters={"tag:maintenance-group" : "rest-prod"})
instances = [i for r in reservations for i in r.instances]
ips = [i.ip_address for i in instances]
q = sqs_conn.create_queue('rest-prod-maint')
m = RawMessage()
msg_src = []
msg_type = []
iid = ["i-9eba6394"]
work_dir="/etc/app/"
services = ["nginx", "php-fpm-5.5"]
webroot="/var/www/html"
#iid = get_instance_metadata()['instance-id']

@app.route('/update', methods = ['POST'])
def ext_inbound():
	# Store request
	rmsg = json.loads(request.data)	
	# Validate sender
	# What's the message say to do?
	if rmsg["commits"] > 0 :
		repo_url = rmsg["repository"]["svn_url"]
		branch = rmsg["repository"]["default_branch"]
		msg = {"repo_url": repo_url, "branch": branch}
		print msg
		# Start update process
		def update():
			g = git.cmd.Git(work_dir)
			g.pull()
			# Insert compile scripts here
			# Stop Services...this needs to not be hard coded
			for s in services:
				subprocess.Popen('sudo service ' + s + ' stop', shell=True)
				# Move old data out
				shutil.move(webroot, "/etc/backup/"+int(time.time()))
				# Copy new data in
				shutil.move(work_dir, webroot)
				# Get an up-to-date config file
				subprocess.Popen('sudo /etc/config/config_dl.sh /etc/config', shell=True)
				# Get everything working again
				for s in services:
					subprocess.Popen('sudo service ' + s + ' start', shell=True)
	# Encode message to go out
	jmsg = json.dumps(msg)
	# Notify maintenance group
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
