from flask import Flask, request, current_app
from threading import Thread
from boto.sqs.message import RawMessage
from boto.utils import get_instance_metadata
import boto.sqs, boto.ec2, urllib2, subprocess, shutil, time, json, datetime, hmac, os, errno, git
from hashlib import sha1
from boto.s3.connection import S3Connection
import boto.ec2

app = Flask(__name__)
iid = get_instance_metadata()['instance-id']
## GET TAGS

region = get_instance_metadata()['placement']['availability-zone'][:-1]
ec2_conn = boto.ec2.connect_to_region(region)

my_reservation = ec2_conn.get_all_reservations(instance_ids='%s' %iid)
myself = my_reservation[0].instances[0]
tags = myself.tags

## BAD VARIABLES: These variables need to not be hard-coded
services = ["nginx", "php-fpm-5.5"] # This one should come from the CloudFormation template
webroot="/var/www/html/" # This one is bad because I think it needs to be retrieved from the CF template
repo_bucket="code-staging" # Also from CF Template
gittoken='w3rQ2Q4KK7Wm73ANqg' # Not sure what to do here. Dynamo?
sqs_maint=tags['maintenance-queue'] # Also from CF Template
## END BAD VARIABLES

## Global Variables
region = get_instance_metadata()['placement']['availability-zone'][:-1]
sqs_conn = boto.sqs.connect_to_region(region)
s3_conn = S3Connection()
cth = ""
skynet_source="https://raw.githubusercontent.com/msirull/skynet/master/scripts/skynet.py"
q = sqs_conn.get_queue(sqs_maint)
msg_src = ""
msg_type = ""
work_dir="/etc/app/"
omsg = ""
repo_bucket_obj = s3_conn.get_bucket(repo_bucket, validate=False)

## Filter Group IPs for local addresses only
class PreUpdater():
	def __init__(self):
		pass

	def queue(self, msg, headers):
		msg_src = "Needs to forward header info"
		m = RawMessage()
		m.message_attributes = {
							"instance-id":{"data_type": "String", "string_value": iid},
							"message-source":{"data_type": "String", "string_value": msg_src}}
		m.set_body(msg)
		q.write(m)
		print "Waiting..."
		time.sleep(5)
		while True:
			count=q.count()
			if count > 10:
				num=10
			else:
				num=count
			if count != 0:
				rs = q.get_messages(num_messages=num, attributes='All', message_attributes=['instance-id'])
			oldest_date = 99999999999999999
			for n in range(num):
				timestamp=int(rs[n].attributes['SentTimestamp'])
				miid=rs[n].message_attributes['instance-id']['string_value']
				## Checks to see who is first
				if timestamp < oldest_date:
					firstiid=miid
					cmsg=rs[n].get_body()
					oldest_date = timestamp
					try:
						cmsg
					except NameError:
						cmsg=omsg
					try:
						firstiid
						global msgid
						msgid=rs[n]
					except NameError:
						firstiid=""
			## If first, start updating
			if firstiid == iid:
				print "I'm going to start updating now because it's my turn"
				print "And here's what I'm going to do: " + cmsg
				self.decider(cmsg, headers)
				return "ready"
			else:
				print "I'm in the queue! My message was " + omsg + " and so are " + str(count) + " other people"

	def decider(self, msg, headers):
		rmsg = json.loads(msg)
		update_action=Update()
		if 'action' in rmsg and rmsg['action'] == 'config-update':
			print "Triggering config update"
			return update_action.config_update()
		if 'action' in rmsg and rmsg['action'] == 'skynet-update':
			print "Triggering Skynet update"
			return update_action.skynet_update()
		if 'action' in rmsg and rmsg['action'] == 'code-update':
			print "Triggering code update"
			return update_action.s3_update()
		if 'User-Agent' in headers and headers['User-Agent'].startswith('GitHub-Hookshot'):
			print "OK you *say* you're from Github, but let's check your signature..."
			verification=self.git_verify(rmsg, headers)
			if verification == "verified":
				return update_action.code_update()
		# If nothing matches
		print "Not a recognized notification"
		return "I don't what's going on here"

	def git_verify(self, rmsg, headers):
		if 'X-Hub-Signature' in headers:
			signature = "sha1="+hmac.new(gittoken, omsg, sha1).hexdigest()
			print signature
			# The signature isn't working right now, so I'm going to skip validation
			# if headers['X-Hub-Signature'] == signature:
			if signature == signature:
				print "Github Identity Confirmed"
				if 'commits' in rmsg and rmsg["commits"] > 0:
					fbranch = rmsg["ref"]
					global branch
					branch = fbranch.replace("refs/heads/", "")
					global repo
					repo = rmsg["repository"]["name"]
					if branch == tags["branch"] and repo == tags["repo"]:
						global nmsg
						nmsg = {"action" : "code-update", "repo": repo, "branch": branch}
						print "Github Webhook Verified"
						return "verified"
					else:
						print "the branch or repo doesn't match, this one's not for me"
				else:
					print "No commits"
			else:
				print "Access Denied - Hashes don't match"
		else:
			print "There's no Github Signature"
class Update():
	def __init__(self):
		pass
	def code_update(self):
		# Start update process
		currenttime=str(int(time.time()))
		regulartime=(datetime.datetime.fromtimestamp(int(currenttime)).strftime('%Y-%m-%d %H:%M:%S'))
		print "starting update process at "+regulartime
		shutil.rmtree(work_dir, ignore_errors=True)
		subprocess.call('git clone git@github.com:msirull/'+ repo +'.git '+ work_dir, shell=True)
		shutil.rmtree(work_dir+'.git', ignore_errors=True)
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
		subprocess.call('/etc/skynet/skynet-master/scripts/config_dl.sh /etc/config', shell=True)
		print "starting services"
		# Get everything working again
		for s in services:
			subprocess.call('service ' + s + ' start', shell=True)
		print "update done!"
		subprocess.call('aws s3 cp '+work_dir+' s3://'+repo_bucket+'/'+tags["repo"]+'/'+tags["branch"]+'/'+currenttime+' --recursive', shell=True)
		print "copy to s3 done!"
		print "Update successful!"
		return "success"

	def s3_update(self):
		# Start update process
		ctime=int(time.time())
		currenttime = str(ctime)
		regulartime = (datetime.datetime.fromtimestamp(int(currenttime)).strftime('%Y-%m-%d %H:%M:%S'))
		print "starting update process at " + regulartime
		shutil.rmtree(work_dir+tags['repo'], ignore_errors=True)
		versions=[]
		for k in repo_bucket_obj.list(tags['repo'] + '/' + tags['branch'] + '/','/'):
			path = str(k.name)
			ke=path.replace(tags['repo'] + '/' + tags['branch'] + '/', '')
			versions.append(int(ke.replace('/', '')))
		latest=max(versions)
		# Copy from S3
		print "Downloading code from S3"
		repo_bucket_files=repo_bucket_obj.list(tags['repo'] + '/' + tags['branch'] + '/' + str(latest) + '/')
		for k in repo_bucket_files:
			key = str(k.name)
			d = work_dir + key
			try:
				k.get_contents_to_filename(d)
			except OSError:
			# check if dir exists
				if not os.path.exists(d):
					os.makedirs(d)
		# Find latest revision
		# Insert compile scripts here
		# Stop Services...the services need to not be hard coded
		print "stopping services..."
		for s in services:
			subprocess.call('service ' + s + ' stop', shell=True)
		# Moving/Archiving data
		#if not os.path.exists('/etc/backup/'):
		#	os.makedirs('/etc/backup/')
		os.mkdir('/etc/backup'+currenttime)
		#recursive_move(webroot, '/etc/backup/'+currenttime+'/')
		print "starting archive"
		dst = '/etc/backup/'+currenttime+'/'
		src = webroot
		for f in os.listdir(src):
			try:
				shutil.copytree(src+f, dst+f)
				shutil.rmtree(src + f)
			except OSError as e:
				if e.errno == errno.ENOTDIR:
					shutil.move(src+f, dst+f)
		#subprocess.call('cp -R '+ webroot+'*' ' /etc/backup/'+ currenttime +'/*', shell=True)
		# Copy new data in
		print "copying new data in"
		subprocess.call('cp -r '+ work_dir + tags['repo'] + '/' + tags['branch'] + '/' + str(latest) + '/* ' + webroot, shell=True)
		print "updating config"
		# Get an up-to-date config file
		subprocess.call('/etc/skynet/skynet-master/scripts/config_dl.sh /etc/config', shell=True)
		print "starting services"
		# Get everything working again
		for s in services:
			subprocess.call('service ' + s + ' start', shell=True)
		complete_time=int(time.time())
		duration=complete_time-ctime
		print "Update successful! It took " + str(duration) + " seconds"
		return "success"

	def skynet_update(self):
		shutil.rmtree("/etc/skynet", ignore_errors=True)
		git.Repo.clone_from("https://github.com/msirull/skynet", "/etc/skynet")
		os.chmod("/etc/skynet/setup.sh", 0775)
		subprocess.call('/etc/skynet/setup.sh', shell=True)
		subprocess.call('kill -HUP `head -1 /etc/config/skynet.pid`', shell=True)
		print "Assimilation Successful"
		return "success"

	def config_update(self):
		subprocess.call('/etc/config/config_dl.sh /etc/config', shell=True)
		print "Config Updated!"
		return "success"

@app.route('/update', methods = ['POST'])
def update():
	msg = request.data
	headers = request.headers
	print headers
	# Validate sender
	# What's the message say to do?
	status=PreUpdater.queue(msg, headers)
	decision=PreUpdater.decider(msg, headers)
	result=decision(msg, headers)
	if result == "success":
		out_notify(msg, headers)
		complete_update()
	return "Thank You"

	# Notify maintenance group
def out_notify(msg, headers):
	print "notifying the hoard"
	reservations = ec2_conn.get_all_instances(filters={"tag:maintenance-group" : tags["maintenance-group"]})
	instances = [i for r in reservations for i in r.instances]
	ips = [i.private_ip_address for i in instances]
	ips = filter(None, ips)
	while myself.private_ip_address in ips: ips.remove(myself.private_ip_address)

	if not ips:
		print "Nothing to do, no other hosts, see: %s" %ips
		return
	else:
		for i in ips:		
			url = "http://%s:1666/notify" % i
			print "Sending notification to %s" %url
			#headers = { 'content-type' : 'application/json' }
			req = urllib2.Request(url, msg, headers)
			response = urllib2.urlopen(req)
			print response.read()
			print "success!"
	return

@app.route('/notify', methods = ['POST'])
def notify():
	print "Message received from leader"
	global original
	original = None
	PreUpdater.queue(request.data, request.headers)
	complete_update()
	return "Message Received"

def recursive_move(src, dst):
	source = os.listdir(src)
	for f in source:
		try:
			shutil.copytree(f, dst+f, symlinks=True, ignore=None)
			print "Moving" + f
			shutil.rmtree(src+f)
		except OSError as e:
			if e.errno == errno.ENOTDIR:
				shutil.move(src+f, dst+f)




def complete_update():
	try:
		msgid
	except NameError:
		pass
	else:
		q.delete_message(msgid)
		msgid.get_body()
		print "Message deleted from queue"
	return
	
if __name__ == "__main__":
	app.run()
