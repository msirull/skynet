from flask import Flask, request, current_app
from threading import Thread
from boto.sqs.message import RawMessage
from boto.utils import get_instance_metadata
import boto.sqs, boto.ec2, urllib2, subprocess, shutil, time, json, datetime, hmac, os, errno, git
from hashlib import sha1
from boto.s3.connection import S3Connection
from boto.ec2 import EC2Connection


app = Flask(__name__)
iid = get_instance_metadata()['instance-id']
## GET TAGS
ec2_conn = EC2Connection()

my_reservation = ec2_conn.get_all_instances(filters={'instance-id': '%s' %iid})
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
repo_bucket_obj = s3_conn.get_bucket(repo_bucket)

## Filter Group IPs for local addresses only
reservations = ec2_conn.get_all_instances(filters={"tag:maintenance-group" : tags["maintenance-group"]})
instances = [i for r in reservations for i in r.instances]
ips = [i.private_ip_address for i in instances]
ips = filter(None, ips)
for i in ips:
	if not i.startswith('192.168') or i.startswith('172.') or i.startswith('10.'):
		ips.remove(i)
while myself.private_ip_address in ips: ips.remove(myself.private_ip_address)

@app.route('/update', methods = ['POST'])
def ext_inbound():
	# Store Request
	global omsg
	omsg = request.data
	global headers
	headers = request.headers
	print headers
	global original
	original = True
	# Validate sender
	# What's the message say to do?
	thr0 = Thread(target=decider)
	thr0.start()
	return "Thank You"


def git_verify():
	rmsg = json.loads(omsg)
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
					thr1 = Thread(target=update)
					thr1.start()
					print "Starting Update"
				else:
					print "the branch or repo doesn't match, this one's not for me"
			else:
				print "No commits"
		else:
			print "Access Denied - Hashes don't match"
	else:
		print "There's no Github Signature"


	# Notify maintenance group
def out_notify(msg):
	print "notifying the hoard"
	if ips == []:
		print "Nothing to do, no other hosts, see: %s" %ips
		return
	else:
		for ip in ips:		
			url = "http://%s/notify" % ip
			print "Sending notification to %s" %url
			#headers = { 'content-type' : 'application/json' }
			req = urllib2.Request(url, msg, headers)
			response = urllib2.urlopen(req)
			print response.read()
			print "success!"
	return

@app.route('/notify', methods = ['POST'])
def in_notify():
	print "Message received from leader"
	global omsg
	omsg = request.data
	rmsg = json.loads(omsg)
	# Get in line
	msg_src = "test inline message source"
	m = RawMessage()
	m.message_attributes = {
						"instance-id":{"data_type": "String", "string_value": iid},
						"message-source":{"data_type": "String", "string_value": msg_src}}
	m.set_body(omsg)
	q.write(m)
	thr = Thread(target=wait)
	thr.start()
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

def update():
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
	thr2 = Thread(target=out_notify)
	thr2.start()
	return
	
def wait():
	time.sleep(2)
	while True:
		count=q.count()
		if count > 10:
			num=10
		else:
			num=count
		rs = q.get_messages(num_messages=num, attributes='All', message_attributes=['instance-id'])
		oldest_date = 99999999999999999 
		for i in range(num):
			timestamp=int(rs[i].attributes['SentTimestamp'])
			miid=rs[i].message_attributes['instance-id']['string_value']
			if timestamp < oldest_date:
				cth=miid
				cmp=rs[i].get_body()
				oldest_date = timestamp
		try:
			cmp
		except NameError:
			cmp=omsg
		try:
			cth
		except NameError:
			cth=""
		if cth == iid:
			global am
			am=rs[i]
			print "I'm going to start updating now because it's my turn"		
			print "And here's what I'm going to do: " + cmp
			thr6 = Thread(target=decider)
			thr6.start() 
			return
		else:
			print "I'm in the queue! My message was " + omsg + " and so are " + str(count) + " other people"
def decider():
	rmsg = json.loads(omsg)
	if 'action' in rmsg and rmsg['action'] == 'config-update':
		subprocess.call('/etc/config/config_dl.sh /etc/config', shell=True)
		print "Config Updated!"
		if original:
			thr7 = Thread(target=out_notify)
			thr7.start()
		thr1 = Thread(target=complete_update)
		thr1.start()
		return
	if 'action' in rmsg and rmsg['action'] == 'skynet-update':
		shutil.rmtree("/etc/skynet", ignore_errors=True)
		git.Repo.clone_from("https://github.com/msirull/skynet", "/etc/skynet")
		os.chmod("/etc/skynet/setup.sh", 0775)
		subprocess.call('/etc/skynet/setup.sh', shell=True)
		subprocess.call('kill -HUP `head -1 /etc/config/skynet.pid`', shell=True)
		print "Assimilation Successful"
		if original:
			out_notify(omsg)
		complete_update()	
		return
	if 'action' in rmsg and rmsg['action'] == 'code-update':
		thr3 = Thread(target=s3_update)
		thr3.start()
		return
	if 'User-Agent' in headers and headers['User-Agent'].startswith('GitHub-Hookshot'):
		print "OK you *say* you're from Github, but let's check your signature..."
		thr2 = Thread(target=git_verify)
		thr2.start()
		return
	# If nothing matches
	print "Not a recognized notification"
	return

def s3_update():
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
	thr4 = Thread(target=complete_update)
	thr4.start()


def complete_update():
	try:
		am
	except NameError:
		am = None
	else:
		pass
	if am:	
		q.delete_message(am)
		am.get_body()
		print "Message deleted from queue"
	return
	
if __name__ == "__main__":
	app.run()
