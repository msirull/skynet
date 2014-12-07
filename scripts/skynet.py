from flask import Flask, request, current_app
from threading import Thread
from boto.sqs.message import RawMessage
from boto.utils import get_instance_metadata
import boto.sqs, boto.ec2, urllib2, git, subprocess, shutil, time, json, datetime, hmac, os, errno
from hashlib import sha1
from boto.s3.connection import S3Connection

app = Flask(__name__)
#iid = get_instance_metadata()['instance-id']
iid = 'i-45s63727s8'
tags = file.read(open("/etc/config/tags.info", "r"))
ptags = json.loads(tags)
region='us-west-2'
#region = get_instance_metadata()['placement']['availability-zone'][:-1]
ec2_conn = boto.ec2.connect_to_region(region)
sqs_conn = boto.sqs.connect_to_region(region)
s3_conn = S3Connection()
cth = ""
skynet_source="https://raw.githubusercontent.com/msirull/skynet/master/scripts/skynet.py"
reservations = ec2_conn.get_all_instances(filters={"tag:maintenance-group" : ptags["maintenance-group"]})
instances = [i for r in reservations for i in r.instances]
ips = [i.ip_address for i in instances]
q = sqs_conn.get_queue(ptags['maintenance-group']+'-maint')
msg_src = ""
msg_type = ""
work_dir="/etc/app/"
services = ["nginx", "php-fpm-5.5"]
webroot="/var/www/html/"
repo_bucket="repo-staging"
gittoken='w3rQ2Q4KK7Wm73ANqg' #I know I need to move this
omsg = ""
repo_bucket_obj = s3_conn.get_bucket(repo_bucket)

@app.route('/update', methods = ['POST'])
def ext_inbound():
	# Store Request
	global omsg
	omsg = request.data
	rmsg = json.loads(request.data)
	# Only move forward if there's a commit
	msg=request.data
	# Decode
	jmsg = json.dumps(msg)		
	print(jmsg)
	global headers
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
			signature = "sha1=5902b5d77eb62fc9650b8cb9697b70f8d700adc6"
			print signature
			if headers['X-Hub-Signature'] == signature:
				print "Github Identity Confirmed"
				if 'commits' in rmsg and rmsg["commits"] > 0:
					fbranch = rmsg["ref"]
					global branch
					branch = fbranch.replace("refs/heads/", "")
					global repo
					repo = rmsg["repository"]["name"]
					if branch == ptags["branch"] and repo == ptags["repo"]:
						msg = {"repo": repo, "branch": branch}
						thr1 = Thread(target=update)
						thr1.start()
						thr2 = Thread(target=out_notify)
						thr2.start()
						return "Starting Update"
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

	# Notify maintenance group
	
def out_notify():
	print "notifying the hoard"
	for ip in ips:
		url = "http://%s/notify" % ip
		print url
		data = omsg
		#headers = { 'content-type' : 'application/json' }
		req = urllib2.Request(url, data, headers)
		print req
		response = urllib2.urlopen(req)
		print response.read()
		print "success!"
	return

@app.route('/notify', methods = ['POST'])
def in_notify():
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
	subprocess.call('/etc/skynet/skynet-master/scripts/config_dl.sh /etc/config', shell=True)
	print "starting services"
	# Get everything working again
	for s in services:
		subprocess.call('service ' + s + ' start', shell=True)
	print "update done!"
	subprocess.call('aws s3 cp '+work_dir+' s3://'+repo_bucket+'/'+ptags["repo"]+'/'+ptags["branch"]+'/'+currenttime+' --recursive', shell=True)
	print "copy to s3 done!"
	print "Update successful!"
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
			thr2 = Thread(target=decider)
			thr2.start() 
			return
		else:
			print "I'm in the queue! My message was " + omsg + " and so are " + str(count) + " other people"
def decider():
	rmsg = json.loads(omsg)
	if 'action' in rmsg and rmsg['action'] == 'config-update':
		subprocess.call('/etc/config/config_dl.sh /etc/config', shell=True)
		print "Config Updated!"
		return complete_update()
	if 'action' in rmsg and rmsg['action'] == 'skynet-update':
		f = urllib2.urlopen(skynet_source)
		ff=open("/etc/config/skynet.py", "w")
		ff.write(f.read())
		ff.close()
		shutil.copy('/etc/config/skynet.py', '/etc/config/skynet_main.py')
		print "Assimilation Successful"
		return complete_update()
	if 'action' in rmsg and rmsg['action'] == 'code-update':
		thr3 = Thread(target=s3_update)
		thr3.start()
		return

def s3_update():
	# Start update process
	currenttime = str(int(time.time()))
	regulartime = (datetime.datetime.fromtimestamp(int(currenttime)).strftime('%Y-%m-%d %H:%M:%S'))
	print "starting update process at " + regulartime
	shutil.rmtree(work_dir+ptags['repo'], ignore_errors=True)	

	# Copy from S3
	print "Downloading code from S3"
	repo_bucket_files=repo_bucket_obj.list()
	for k in repo_bucket_files:
		key = str(k.key)
		d = work_dir + key
		try:
			k.get_contents_to_filename(d)
		except OSError:
		# check if dir exists
			if not os.path.exists(d):
				os.makedirs(d)
	# Find latest revision
	repo_dir = os.listdir(work_dir+ ptags['repo'] + '/' + ptags['branch'] + '/')
	latest = max(map(int,repo_dir))
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
	subprocess.call('cp -r '+ work_dir + ptags['repo'] + '/' + ptags['branch'] + '/' + str(latest) + '/* ' + webroot, shell=True)
	print "updating config"
	# Get an up-to-date config file
	subprocess.call('/etc/skynet/skynet-master/scripts/config_dl.sh /etc/config', shell=True)
	print "starting services"
	# Get everything working again
	for s in services:
		subprocess.call('service ' + s + ' start', shell=True)
	print "Update successful! It took " + str(int(time.time())-(int(currenttime))) + " seconds"
	return complete_update()

def complete_update():
	q.delete_message(am)
	am.get_body()
	print "Message deleted from queue"
	return
	
if __name__ == "__main__":
	app.run(port=1666, debug=True)
