from flask import Flask, request
from boto.utils import get_instance_metadata
import boto.ec2, boto.ec2, urllib2, shutil, os, errno, updater, logging, time, datetime
logging.basicConfig(filename='/var/log/skynet/skynet.log',level=logging.INFO)

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
	regulartime=(datetime.datetime.fromtimestamp(int(time.time())).strftime('%Y-%m-%d %H:%M:%S'))
	logging.info("Message received at %s", regulartime)
	msg = request.data
	headers = request.headers
	logging.debug(headers)
	logging.debug(msg)
	# Validate sender
	# What's the message say to do?
	preupdate=updater.PreUpdater()
	status=preupdate.queue(msg, headers)
	decision=preupdate.decider(msg, headers)
	result=decision()
	if result == "success":
		updater.complete_update()
		out_notify(msg, headers)
	logging.info("Update completed successfully")
	return "Success"

	# Notify maintenance group
def out_notify(msg, headers):
	logging.info("notifying the hoard")
	reservations = ec2_conn.get_all_instances(filters={"tag:maintenance-group" : tags["maintenance-group"]})
	instances = [i for r in reservations for i in r.instances]
	ips = [i.private_ip_address for i in instances]
	ips = filter(None, ips)
	while myself.private_ip_address in ips: ips.remove(myself.private_ip_address)

	if not ips:
		logging.info("Nothing to do, no other hosts, see: %s", ips)
		return
	else:
		for i in ips:
			url = "http://%s:1666/notify" % i
			logging.info("Sending notification to %s", url)
			#headers = { 'content-type' : 'application/json' }
			req = urllib2.Request(url, msg, headers)
			response = urllib2.urlopen(req)
			logging.debug(response.read())
			logging.info("success!")
	return

@app.route('/notify', methods = ['POST'])
def notify():
	regulartime=(datetime.datetime.fromtimestamp(int(time.time())).strftime('%Y-%m-%d %H:%M:%S'))
	logging.info("Message received from leader at %s", regulartime)
	global original
	original = None
	preupdate2=updater.PreUpdater()
	status=preupdate2.queue(request.data, request.headers)
	decision=preupdate2.decider(request.data, request.headers)
	result=decision()
	updater.complete_update()
	return "Message Received"

def recursive_move(src, dst):
	source = os.listdir(src)
	for f in source:
		try:
			shutil.copytree(f, dst+f, symlinks=True, ignore=None)
			logging.info("Moving" + f)
			shutil.rmtree(src+f)
		except OSError as e:
			if e.errno == errno.ENOTDIR:
				shutil.move(src+f, dst+f)
	
if __name__ == "__main__":
	app.run()
