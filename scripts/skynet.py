from flask import Flask, request
from boto.utils import get_instance_metadata
import boto.ec2, boto.ec2, urllib2, shutil, os, errno, updater

app = Flask(__name__)
iid = get_instance_metadata()['instance-id']
## GET TAGS

region = get_instance_metadata()['placement']['availability-zone'][:-1]
ec2_conn = boto.ec2.connect_to_region(region)

my_reservation = ec2_conn.get_all_reservations(instance_ids='%s' %iid)
myself = my_reservation[0].instances[0]
tags = myself.tags


## Global Namespace
cth = ""
skynet_source="https://raw.githubusercontent.com/msirull/skynet/master/scripts/skynet.py"
msg_src = ""
msg_type = ""
work_dir="/etc/app/"
omsg = ""

@app.route('/update', methods = ['POST'])
def update():
	msg = request.data
	headers = request.headers
	print headers
	print msg
	# Validate sender
	# What's the message say to do?
	preupdate=updater.PreUpdater()
	status=preupdate.queue(msg, headers)
	decision=preupdate.decider(msg, headers)
	result=decision()
	if result == "success":
		updater.complete_update()
		out_notify(msg, headers)
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
	preupdate2=updater.PreUpdater()
	preupdate2.queue(request.data, request.headers)
	updater.complete_update()
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
	
if __name__ == "__main__":
	app.run()
