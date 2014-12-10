from boto.dynamodb2.table import Table
import json, os, subprocess
from boto.utils import get_instance_metadata

tags = file.read(open("/etc/config/tags.info", "r"))
ptags = json.loads(tags)
# Add default endpoint locations into Nginx
if os.path.exists("/etc/config/rp.locations"):
	os.remove("/etc/config/rp.locations")
env = ptags['environment']
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
env = ptags['environment']
tbl = "endpoints"
locations = {}
table_obj = Table(tbl)
stack_items = table_obj.query_2(env__eq=env)

## Add default routing to self for Skynet in Nginx
file = open("/etc/config/rpc.locations", "a")
file.write("location / {\n")
file.write("proxy_pass http://localhost:666/;"+"\n")
file.write("}\n")
file.close()
## Add data from DynamoDB endpoints table
for items in stack_items:
	stack=items['layer']+"/"+items['env']
	url=items['url']
	if stack == (ptags['layer'] + '/' + env) or stack == "/":
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