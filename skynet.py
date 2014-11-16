from flask import Flask, render_template, request, jsonify, json
import boto.sqs
from boto.sqs.message import RawMessage
from boto.utils import get_instance_metadata
import boto.ec2
import urllib2

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
iid = ["i-9eba7394"]
#iid = get_instance_metadata()['instance-id']


@app.route('/update', methods = ['POST'])
def ext_inbound():
	omsg = request.data
	print omsg
	#store request
	rmsg = json.loads(request.data)
	#validate sender
	if request.method == 'POST' and rmsg["Type"] == "Notification" :
		msg = rmsg["Message"]
	#decode
	jmsg = json.dumps(msg)		
	print(jmsg)
	#print request.data
	iid = "test inline iid"
	msg_src = "test inline message source"
	m.message_attributes = {
						"instance-id":{"data_type": "String", "string_value": iid},
						"message-source":{"data_type": "String", "string_value": msg_src}}
	m.set_body(omsg)
	q.write(m)
	#notify maintenance group
	for ip in ips:
		url = "http://%s/notify" % ip
		def out_notify():			
			print url
			data = omsg
			headers = { 'content-type' : 'application/json' }
			req = urllib2.Request(url, data, headers)
			print req
			response = urllib2.urlopen(req)
			print response.read()
	return "success!"

@app.route('/notify', methods = ['POST'])
def in_notify():
	omsg = request.data
	rmsg = json.loads(request.data)
	#validate sender
	if request.method == 'POST' and rmsg["Type"] == "Notification" :
		msg = rmsg["Message"]
	#decode
	iid = "test inline iid"
	msg_src = "test inline message source"
	m.message_attributes = {
						"instance-id":{"data_type": "String", "string_value": iid},
						"message-source":{"data_type": "String", "string_value": msg_src}}
	m.set_body(omsg)
	q.write(m)
	return "Success iid"
	
	

if __name__ == "__main__":
	app.run(debug=True, port=666)
