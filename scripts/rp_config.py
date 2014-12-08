from boto.dynamodb2.table import Table
import json, os, subprocess
from boto.utils import get_instance_metadata

tags = file.read(open("/etc/config/tags.info", "r"))
ptags = json.loads(tags)
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
	file = open("/etc/config/rp.locations", "w+")
	file.write("location /" + stack +"/ {\n")
	file.write("proxy_pass http://"+ locations[stack] +"/;"+"\n")
	file.write("proxy_redirect http://"+ locations[stack] +"/ /"+stack+"/;\n")
	file.write("}\n")
	file.close()
subprocess.call('service nginx reload', shell=True)

if os.path.exists("/etc/config/rpc.locations"):
	os.remove("/etc/config/rpc.locations")
env = ptags['environment']
tbl = "endpoints"
locations = {}
table_obj = Table(tbl)
stack_items = table_obj.query_2(env__eq=env)
for items in stack_items:
	stack=items['layer']+"/"+items['env']
	url=items['url']
	locations[stack] = url
	file = open("/etc/config/rpc.locations", "w+")
	file.write("location /" + stack +"/ {\n")
	file.write("proxy_pass http://"+ locations[stack] +":1666;"+"\n")
	file.write("proxy_redirect http://"+ locations[stack] +"/ /"+stack+"/;\n")
	file.write("}\n")
	file.close()
subprocess.call('service nginx reload', shell=True)