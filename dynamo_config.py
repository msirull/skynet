from boto.dynamodb2.table import Table
import json, os
from boto.utils import get_instance_metadata
region="us-west-2"
region = get_instance_metadata()['placement']['availability-zone'][:-1]
def create_boto_config():
	file = open("/etc/boto.cfg", "a")
	file.write("[DynamoDB]\n")
	file.write("region = '" + region +"'\n")
	file.close()
tags = file.read(open("/etc/config/tags.info", "r"))
ptags = json.loads(tags)
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
	file = open("/temp/rp.locations", "a")
	file.write("location /" + stack +"/\n")
	file.write("{proxy_pass http://"+ locations[stack] +";}"+"\n")
	file.close()