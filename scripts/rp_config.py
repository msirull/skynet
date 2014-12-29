from boto.dynamodb2.table import Table
import json, os, subprocess
from boto.utils import get_instance_metadata
import boto.ec2
region = get_instance_metadata()['placement']['availability-zone'][:-1]
ec2_conn = boto.ec2.connect_to_region(region)

iid = get_instance_metadata()['instance-id']
reservations = ec2_conn.get_all_reservations(instance_ids='%s' %iid)
instance = reservations[0].instances[0]
tags= instance.tags
# Add default endpoint locations into Nginx
if os.path.exists("/etc/config/rp.locations"):
	os.remove("/etc/config/rp.locations")
env = tags['environment']
tbl = "endpoints"
locations = {}
table_obj = Table(tbl)
stack_items = table_obj.query_2(env__eq=env)
for items in stack_items:
	stack=items['layer']+"/"+items['env']
	url=items['url']
	locations[stack] = url
	file = open("/etc/config/rp.locations", "a")
	file.write("location /" + stack +"/ {\n")
	file.write("proxy_pass http://"+ locations[stack] +"/;"+"\n")
	file.write("}\n")
	file.close()
subprocess.call('service nginx reload', shell=True)

## Add Skynet endpoint locations into Nginx
if os.path.exists("/etc/config/rpc.locations"):
	os.remove("/etc/config/rpc.locations")
env = tags['environment']
tbl = "endpoints"
locations = {}
table_obj = Table(tbl)
stack_items = table_obj.query_2(env__eq=env)


## Add data from DynamoDB endpoints table
for items in stack_items:
	stack=items['layer']+"/"+items['env']
	url=items['url']
	if stack == (tags['layer'] + '/' + env) or stack == "/":
		locations[stack] = '127.0.0.1'
		port='666'
	else:
		locations[stack] = url
		port='1666'
	file = open("/etc/config/rpc.locations", "a")
	file.write("location /" + stack +"/ {\n")
	file.write("proxy_pass http://"+ locations[stack] +":" + port + "/;"+"\n")
	file.write("}\n")
	file.close()
subprocess.call('service nginx reload', shell=True)